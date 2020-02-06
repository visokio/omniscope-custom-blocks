library(omniscope.api)
library(data.table)

omni.api = omniscope.api()


left = read.input.records(omni.api, input.number=1)
right = read.input.records(omni.api, input.number=2)

value.field = get.option(omni.api, "value")
start.field = get.option(omni.api, "start")
startComparator = get.option(omni.api, "startOperator")
end.field = get.option(omni.api, "end")
endComparator = get.option(omni.api, "endOperator")

#sanity checks
if (is.null(left)) abort(omni.api, "No 'value' input data")
if (is.null(right)) abort(omni.api, "No 'interval' input data")

if ("value.field.internal.omniscope" %in% names(left)) abort(omni.api, "\"value.field.internal.omniscope\" is used internally by this block. The left input data cannot contain a field with this name.")
if ("start.field.internal.omniscope" %in% names(right)) abort(omni.api, "\"start.field.internal.omniscope\" is used internally by this block. The right input data cannot contain a field with this name.")
if ("end.field.internal.omniscope" %in% names(right)) abort(omni.api, "\"end.field.internal.omniscope\" is used internally by this block. The right input data cannot contain a field with this name.")

n <- unique(c(names(left), names(right)))

left$value.field.internal.omniscope = left[, value.field]
right$start.field.internal.omniscope = right[, start.field]
right$end.field.internal.omniscope = right[, end.field]

left <- left[complete.cases(left[, value.field]), ]
right <- right[complete.cases(right[, c(start.field, end.field)]), ]



is.date <- function(x) {class(x)[1] %in% c("POSIXct", "POSIXt")}

if (!is.numeric(left[, value.field]) && !is.date(left[, value.field])) abort(omni.api, "\"Value field\" must be numeric or date")
if (!is.numeric(right[, start.field]) && !is.date(right[, start.field])) abort(omni.api, "\"Interval start field\" must be numeric or date")
if (!is.numeric(right[, end.field]) && !is.date(right[, end.field])) abort(omni.api, "\"Interval end field\" must be numeric or date")



setDT(left)
setDT(right)


join.on = c(paste("value.field.internal.omniscope", startComparator, "start.field.internal.omniscope", sep=""),
			paste("value.field.internal.omniscope", endComparator, "end.field.internal.omniscope", sep=""))

output.data <- left[right, on=join.on, allow.cartesian = T, nomatch=0, n, with=FALSE]

if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)