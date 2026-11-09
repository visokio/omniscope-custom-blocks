library(omniscope.api)
library(data.table)
omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
path.field = get.option(omni.api, "pathField")
folder = get.option(omni.api, "folder")
recursive = isTRUE(get.option(omni.api, "recursive"))
scan.first = isTRUE(get.option(omni.api, "scanFirst"))
action.additional.fields = get.option(omni.api, "actionAdditionalFields")
action.missing.fields = get.option(omni.api, "actionMissingFields")
action.incorrect.type = get.option(omni.api, "actionIncorrectFieldType")
add.source.field = isTRUE(get.option(omni.api, "addSourceField"))
source.field.name = get.option(omni.api, "sourceFieldName")

blank = function(x) is.null(x) || length(x) == 0 || is.na(x[1]) || trimws(as.character(x[1])) == ""
if (blank(action.additional.fields)) action.additional.fields = "ERROR"
if (blank(action.missing.fields)) action.missing.fields = "ERROR"
if (blank(action.incorrect.type)) action.incorrect.type = "ERROR"
if (blank(source.field.name)) source.field.name = "Source"
source.field.name = trimws(source.field.name)

warnings.list = character(0)

# What to do about a difference: "WARN" (fix it and note it), "IGNORE" (fix it), "ERROR" (stop).
handle = function(action, text) {
  if (action == "ERROR") abort(omni.api, text)
  if (action == "WARN") warnings.list <<- c(warnings.list, text)
}

# ---- the list of files

if (!is.null(input.data)) {
  if (blank(path.field)) abort(omni.api, "An input is connected: choose the field that holds the file paths in \"Path field\".")
  if (!(path.field %in% names(input.data))) abort(omni.api, paste0("The input has no field called '", path.field, "'."))
  file.list = as.character(input.data[[path.field]])
  file.list = trimws(file.list[!is.na(file.list) & trimws(file.list) != ""])
  if (length(file.list) == 0) abort(omni.api, paste0("The field '", path.field, "' holds no file paths."))
} else {
  if (blank(folder)) abort(omni.api, "Choose a folder, or connect an input with a field of file paths.")
  folder = as.character(folder)
  if (!dir.exists(folder)) abort(omni.api, paste0("Folder not found: ", folder))
  file.list = sort(list.files(folder, pattern = "\\.rds$", ignore.case = TRUE, recursive = recursive, full.names = TRUE))
  if (length(file.list) == 0) {
    abort(omni.api, paste0("No .rds files in ", folder, if (recursive) " or its subfolders" else "",
                           if (!recursive) " (tick Recursive to search subfolders)" else ""))
  }
}

# ---- reading one file

type.of = function(col) {
  if (is.logical(col)) return("logical")
  if (is.integer(col)) return("int")
  if (is.numeric(col)) return("float")
  if (inherits(col, "POSIXct")) return("datetime")
  "text"
}

# Types Omniscope reads: factors as text, dates as date-times (midnight UTC), lists as comma-joined text.
normalise = function(dt) {
  for (n in names(dt)) {
    col = dt[[n]]
    if (is.factor(col)) col = as.character(col)
    else if (inherits(col, "POSIXlt")) col = as.POSIXct(col)
    else if (inherits(col, "Date")) col = as.POSIXct(format(col), tz = "UTC")
    else if (inherits(col, "difftime")) col = as.numeric(col)
    else if (is.list(col)) col = vapply(col, function(v) paste(format(unlist(v)), collapse = ", "), "")
    else if (!(is.logical(col) || is.numeric(col) || is.character(col) || inherits(col, "POSIXct"))) {
      col = as.character(col)
    }
    set(dt, j = n, value = col)
  }
  dt
}

read.one = function(f) {
  if (!file.exists(f)) abort(omni.api, paste0("File not found: ", f))
  x = tryCatch(readRDS(f), error = function(e) e)
  if (inherits(x, "error")) abort(omni.api, paste0("Could not read ", f, " as a .rds file: ", conditionMessage(x)))
  if (!(is.data.frame(x) || is.matrix(x))) {
    abort(omni.api, paste0(f, " holds a ", paste(class(x), collapse = ", "), ", not a data frame."))
  }
  dt = as.data.table(x)
  if (anyDuplicated(names(dt))) setnames(dt, make.unique(names(dt), sep = " "))
  normalise(dt)
}

coerce = function(col, type) {
  switch(type,
    logical = as.logical(col),
    int = suppressWarnings(as.integer(col)),
    float = suppressWarnings(as.numeric(col)),
    datetime = if (inherits(col, "POSIXct")) col else suppressWarnings(as.POSIXct(as.character(col), tz = "UTC",
                 tryFormats = c("%Y-%m-%d %H:%M:%OS", "%Y-%m-%dT%H:%M:%OS", "%Y-%m-%d %H:%M", "%Y-%m-%d"), optional = TRUE)),
    text = if (inherits(col, "POSIXct")) format(col, "%Y-%m-%d %H:%M:%S", tz = "UTC") else as.character(col)
  )
}

typed.na = function(type, n) {
  switch(type, logical = rep(NA, n), int = rep(NA_integer_, n), float = rep(NA_real_, n),
         datetime = as.POSIXct(rep(NA_real_, n), origin = "1970-01-01", tz = "UTC"), text = rep(NA_character_, n))
}

# ---- the schema: from every file (scan first) or from the first file

schema.names = character(0)
schema.types = character(0)

add.to.schema = function(dt, widen) {
  for (n in names(dt)) {
    t = type.of(dt[[n]])
    if (!(n %in% schema.names)) {
      schema.names <<- c(schema.names, n)
      schema.types <<- c(schema.types, t)
    } else if (widen && t != schema.types[match(n, schema.names)]) {
      i = match(n, schema.names)
      # whole numbers and decimals in different files: decimals for all
      if (setequal(c(t, schema.types[i]), c("int", "float"))) schema.types[i] <<- "float"
    }
  }
}

if (scan.first) {
  for (f in file.list) add.to.schema(read.one(f), widen = TRUE)
}

if (add.source.field && source.field.name %in% schema.names) {
  abort(omni.api, paste0("The files already have a field called '", source.field.name, "': choose another source field name."))
}

# ---- read, align and write each file

total.records = 0
for (f in file.list) {
  dt = read.one(f)
  if (length(schema.names) == 0) add.to.schema(dt, widen = FALSE)
  if (add.source.field && source.field.name %in% names(dt)) {
    abort(omni.api, paste0(f, " already has a field called '", source.field.name, "': choose another source field name."))
  }

  missing.fields = setdiff(schema.names, names(dt))
  if (length(missing.fields) > 0) {
    # with scan first, the schema is every file's fields put together, so missing fields are expected
    if (!scan.first) handle(action.missing.fields, paste0(f, " is missing fields: ", paste(missing.fields, collapse = ", ")))
    for (n in missing.fields) set(dt, j = n, value = typed.na(schema.types[match(n, schema.names)], nrow(dt)))
  }

  extra.fields = setdiff(names(dt), schema.names)
  if (length(extra.fields) > 0) {
    handle(action.additional.fields, paste0(f, " has additional fields, left out: ", paste(extra.fields, collapse = ", ")))
    dt[, (extra.fields) := NULL]
  }

  for (n in schema.names) {
    want = schema.types[match(n, schema.names)]
    have = type.of(dt[[n]])
    if (have == want) next
    if (!(have == "int" && want == "float")) {  # widening whole numbers to decimals loses nothing
      handle(action.incorrect.type, paste0(f, ": field '", n, "' is ", have, ", expected ", want))
    }
    set(dt, j = n, value = coerce(dt[[n]], want))
  }

  setcolorder(dt, schema.names)
  if (add.source.field) dt[, (source.field.name) := f]

  write.output.records(omni.api, as.data.frame(dt), output.number=1)
  total.records = total.records + nrow(dt)
}

message = paste0("Appended ", length(file.list), " file", if (length(file.list) != 1) "s" else "", ", ",
                 format(total.records, big.mark = ",", scientific = FALSE), " records.")
if (length(warnings.list) > 0) {
  shown = head(warnings.list, 5)
  more = length(warnings.list) - length(shown)
  message = paste0(message, " Warnings: ", paste(shown, collapse = "; "),
                   if (more > 0) paste0("; and ", more, " more") else "")
  update.message(omni.api, message)
}
close(omni.api, message)
