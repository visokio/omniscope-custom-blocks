library(omniscope.api)
library(tools)

omni.api = omniscope.api()

file.option = get.option(omni.api, "rda_file")
object.option = get.option(omni.api, "obj")

blank = function(x) is.null(x) || length(x) == 0 || is.na(x[1]) || trimws(as.character(x[1])) == ""

if (blank(file.option)) abort(omni.api, "Choose an R data file (.rds, .rda or .RData) in the option \"R data file\".")
file.path.option = as.character(file.option)
if (!file.exists(file.path.option) || dir.exists(file.path.option)) {
  abort(omni.api, paste0("File not found: ", file.path.option))
}
object.name = if (blank(object.option)) NULL else trimws(as.character(object.option))

ext = tolower(file_ext(file.path.option))
if (!(ext %in% c("rds", "rda", "rdata"))) {
  abort(omni.api, paste0("Unsupported file type '.", ext, "': choose a .rds, .rda or .RData file."))
}

# Read the file into a named list of objects, in the order they were saved.
read.objects = function(path, ext) {
  if (ext == "rds") {
    objs = list(readRDS(path))
    names(objs) = file_path_sans_ext(basename(path))
    return(objs)
  }
  env = new.env()
  saved = load(path, envir = env)
  mget(saved, envir = env)
}

objects = tryCatch(read.objects(file.path.option, ext), error = function(e) e)
if (inherits(objects, "error")) {
  abort(omni.api, paste0("Could not read ", basename(file.path.option), " as an R data file: ", conditionMessage(objects)))
}
if (length(objects) == 0) abort(omni.api, "The file contains no objects.")

is.table = function(x) is.data.frame(x) || is.matrix(x)
is.convertible = function(x) {
  if (is.table(x)) return(TRUE)
  if (is.atomic(x) && is.null(dim(x))) return(TRUE)
  if (is.list(x) && length(x) > 0 && all(vapply(x, function(v) is.atomic(v) && is.null(dim(v)), TRUE))) {
    lens = lengths(x)
    return(all(lens == lens[1]))
  }
  FALSE
}

describe = function(name, x) {
  df = if (is.convertible(x)) tryCatch(as.table.frame(x, name), error = function(e) NULL) else NULL
  data.frame(
    Object = name,
    Class = paste(class(x), collapse = ", "),
    Records = if (is.null(df)) NA_integer_ else nrow(df),
    Fields = if (is.null(df)) NA_integer_ else ncol(df),
    Readable = !is.null(df),
    stringsAsFactors = FALSE
  )
}

# Turn an object into a data frame with types Omniscope reads.
as.table.frame = function(x, name) {
  if (is.data.frame(x)) {
    df = x
    class(df) = "data.frame"  # tibble, data.table and similar
  } else if (is.matrix(x)) {
    df = as.data.frame(x, stringsAsFactors = FALSE)
  } else if (is.list(x)) {
    df = as.data.frame(x, stringsAsFactors = FALSE, optional = TRUE)
  } else {
    df = if (is.null(names(x))) {
      data.frame(Value = unname(x), stringsAsFactors = FALSE)
    } else {
      data.frame(Name = names(x), Value = unname(x), stringsAsFactors = FALSE)
    }
  }
  automatic.row.names = .row_names_info(df) < 0
  nms = names(df)
  if (is.null(nms)) nms = rep("", ncol(df))
  nms[is.na(nms) | trimws(nms) == ""] = paste("Field", which(is.na(nms) | trimws(nms) == ""))
  names(df) = nms
  for (n in seq_along(df)) {
    col = df[[n]]
    if (is.factor(col)) col = as.character(col)
    else if (inherits(col, "POSIXlt")) col = as.POSIXct(col)
    else if (inherits(col, "Date")) col = as.POSIXct(format(col), tz = "UTC")
    else if (inherits(col, "difftime")) col = as.numeric(col)
    else if (is.complex(col)) col = as.character(col)
    else if (is.list(col)) col = vapply(col, function(v) paste(format(unlist(v)), collapse = ", "), "")
    else if (!is.null(dim(col))) col = apply(col, 1, function(v) paste(v, collapse = ", "))
    attr(col, "label") = NULL
    df[[n]] = col
  }
  if (!automatic.row.names && nrow(df) > 0) {
    df = cbind(data.frame(`Row name` = rownames(df), check.names = FALSE, stringsAsFactors = FALSE), df)
  }
  rownames(df) = NULL
  names(df) = make.unique(names(df), sep = " ")
  df
}

objects.list = do.call(rbind, lapply(names(objects), function(n) describe(n, objects[[n]])))

if (is.null(object.name)) {
  # The first data frame or matrix in the order saved; failing that, the first object that converts.
  tables = names(objects)[vapply(objects, is.table, TRUE)]
  readable = objects.list$Object[objects.list$Readable]
  candidates = c(tables, readable)
  if (length(candidates) == 0) {
    abort(omni.api, paste0("No object in the file can be read as a table. Objects: ",
                           paste0(objects.list$Object, " (", objects.list$Class, ")", collapse = ", ")))
  }
  object.name = candidates[1]
} else if (!(object.name %in% names(objects))) {
  if (ext == "rds") {
    abort(omni.api, "A .rds file holds a single object: leave \"Object to load\" empty.")
  }
  abort(omni.api, paste0("The file has no object called '", object.name, "'. Objects in the file: ",
                         paste(names(objects), collapse = ", ")))
}

x = objects[[object.name]]
if (!is.convertible(x)) {
  abort(omni.api, paste0("'", object.name, "' is a ", paste(class(x), collapse = ", "),
                         ", which cannot be read as a table."))
}
data = as.table.frame(x, object.name)
objects.list$Loaded = objects.list$Object == object.name

write.output.records(omni.api, data, output.number = 1)
write.output.records(omni.api, objects.list, output.number = 2)
close(omni.api, paste0("Loaded '", object.name, "': ", nrow(data), " records, ", ncol(data), " fields."))
