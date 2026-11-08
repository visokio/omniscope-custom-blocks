library(omniscope.api)
suppressPackageStartupMessages(library(data.table))

omni.api = omniscope.api()

left = read.input.records(omni.api, input.number=1)
right = read.input.records(omni.api, input.number=2)

left.field = get.option(omni.api, "left")
comparator = get.option(omni.api, "comparator")
right.field = get.option(omni.api, "right")
left.key = get.option(omni.api, "leftKey")
right.key = get.option(omni.api, "rightKey")
join.type = get.option(omni.api, "joinType")

is.set <- function(x) !is.null(x) && length(x) == 1 && !is.na(x) && nzchar(x)
if (!is.set(comparator)) comparator <- ">="
if (!is.set(join.type)) join.type <- "inner"

# sanity checks
if (is.null(left)) abort(omni.api, "Connect the first (left) input.")
if (is.null(right)) abort(omni.api, "Connect the second (right) input.")
if (!(comparator %in% c("==", "<=", ">=", "<", ">"))) abort(omni.api, paste0("Unknown comparator \"", comparator, "\"."))

check.field <- function(field, data, title, which) {
  if (!is.set(field)) abort(omni.api, paste0("Choose the \"", title, "\"."))
  if (!(field %in% names(data))) abort(omni.api, paste0("The ", which, " input has no field called \"", field, "\"."))
}
check.field(left.field, left, "Left field", "first")
check.field(right.field, right, "Right field", "second")
use.key <- is.set(left.key) || is.set(right.key)
if (use.key) {
  if (!is.set(left.key) || !is.set(right.key)) {
    abort(omni.api, "To match on a field as well, choose it for both inputs; or clear both.")
  }
  check.field(left.key, left, "Equal field in the first input", "first")
  check.field(right.key, right, "Equal field in the second input", "second")
}

kind <- function(x) {
  if (inherits(x, c("POSIXct", "Date"))) return("date")
  if (is.numeric(x)) return("number")
  if (all(is.na(x))) return("empty")  # no values at all: fits either kind
  "other"
}
lk <- kind(left[[left.field]])
rk <- kind(right[[right.field]])
if (lk == "other") abort(omni.api, paste0("\"", left.field, "\" (Left field) must be a number or date field."))
if (rk == "other") abort(omni.api, paste0("\"", right.field, "\" (Right field) must be a number or date field."))
if (lk != "empty" && rk != "empty" && lk != rk) {
  abort(omni.api, "The left and right fields must both be numbers or both be dates.")
}
as.comparable <- function(x) if (inherits(x, c("POSIXct", "Date"))) as.numeric(as.POSIXct(x)) else as.numeric(x)
if (use.key) {
  kl <- left[[left.key]]
  kr <- right[[right.key]]
  if (is.numeric(kl) != is.numeric(kr) || inherits(kl, "POSIXct") != inherits(kr, "POSIXct")) {
    abort(omni.api, "The two equal fields must be of the same type (both text, both numbers or both dates).")
  }
  if (inherits(kl, "POSIXct")) { kl <- as.numeric(kl); kr <- as.numeric(kr) }
  if (is.numeric(kl)) { kl <- as.numeric(kl); kr <- as.numeric(kr) }
}

# Join row numbers only, on helper columns, then build the output from the inputs as they are
x <- data.table(.lrow = seq_len(nrow(left)), .lv = as.comparable(left[[left.field]]))
i <- data.table(.rrow = seq_len(nrow(right)), .rv = as.comparable(right[[right.field]]))
on <- paste0(".lv", comparator, ".rv")
if (use.key) {
  x[, .lk := kl]
  i[, .rk := kr]
  on <- c(".lk==.rk", on)
  x <- x[!is.na(.lk)]
  i <- i[!is.na(.rk)]
}
x <- x[!is.na(.lv)]  # missing values match nothing
i <- i[!is.na(.rv)]

pairs <- x[i, on = on, .(.lrow = x..lrow, .rrow = i..rrow), nomatch = NULL, allow.cartesian = TRUE]
matched <- length(unique(pairs$.lrow))
if (join.type == "left") {
  missing.rows <- setdiff(seq_len(nrow(left)), pairs$.lrow)
  pairs <- rbind(pairs, data.table(.lrow = missing.rows, .rrow = rep(NA_integer_, length(missing.rows))))
}
setorder(pairs, .lrow, .rrow, na.last = TRUE)  # first input's order, then the second input's

left.part <- as.data.frame(left)[pairs$.lrow, , drop = FALSE]
right.part <- as.data.frame(right)[pairs$.rrow, , drop = FALSE]  # NA row number: empty fields
output.data <- cbind(left.part, right.part)
names(output.data) <- make.unique(c(names(left), names(right)), sep = ".")  # a name in both: ".1" on the second
rownames(output.data) <- NULL

write.output.records(omni.api, output.data, output.number=1)
close(omni.api, paste0(matched, " of ", nrow(left), " first-input records matched; ", nrow(output.data), " records out"))
