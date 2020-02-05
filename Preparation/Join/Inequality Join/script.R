library(omniscope.api)
library(data.table)

omni.api = omniscope.api()


left = read.input.records(omni.api, input.number=1)
right = read.input.records(omni.api, input.number=2)

left.field = get.option(omni.api, "left")
comparator = get.option(omni.api, "comparator")
right.field = get.option(omni.api, "right")

#sanity checks
if (is.null(left)) abort(omni.api, "No 'left' input data")
if (is.null(right)) abort(omni.api, "No 'right' input data")

if ("left.field.internal.omniscope" %in% names(left)) abort(omni.api, "\"left.field.internal.omniscope\" is used internally by this block. The left input data cannot contain a field with this name.")
if ("right.field.internal.omniscope" %in% names(right)) abort(omni.api, "\"right.field.internal.omniscope\" is used internally by this block. The right input data cannot contain a field with this name.")


left$left.field.internal.omniscope = left[, left.field]
right$right.field.internal.omniscope = right[, right.field]

left <- left[complete.cases(left[, left.field]), ]
right <- right[complete.cases(right[, right.field]), ]

is.date <- function(x) {class(x)[1] %in% c("POSIXct", "POSIXt")}

if (!is.numeric(left[, left.field]) && !is.date(left[, left.field])) abort(omni.api, "\"Left field\" must be numeric or date")
if (!is.numeric(right[, right.field]) && !is.date(right[, right.field])) abort(omni.api, "\"Right field\" must be numeric or date")



setDT(left)
setDT(right)


join.on = paste("left.field.internal.omniscope", comparator, "right.field.internal.omniscope", sep="")

output.data <- left[right, on=c(join.on), allow.cartesian = T, nomatch=0]

output.data[, c("left.field.internal.omniscope") := NULL]

if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)
