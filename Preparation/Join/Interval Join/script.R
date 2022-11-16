library(omniscope.api)
library(data.table)
library(dplyr)

omni.api = omniscope.api()


left = read.input.records(omni.api, input.number=1)
right = read.input.records(omni.api, input.number=2)

value.field = get.option(omni.api, "value")
start.field = get.option(omni.api, "start")
startComparator = get.option(omni.api, "startOperator")
end.field = get.option(omni.api, "end")
endComparator = get.option(omni.api, "endOperator")
join.type = get.option(omni.api, "joinType")

left.eq.field = get.option(omni.api, "left")
right.eq.field = get.option(omni.api, "right")

has.eq.crit = !is.null(left.eq.field) && left.eq.field != "" && !is.null(right.eq.field) && right.eq.field != ""


#sanity checks
if (is.null(left)) abort(omni.api, "No 'value' input data")
if (is.null(right)) abort(omni.api, "No 'interval' input data")

if ("value.field.internal.omniscope" %in% names(left)) abort(omni.api, "\"value.field.internal.omniscope\" is used internally by this block. The left input data cannot contain a field with this name.")
if ("start.field.internal.omniscope" %in% names(right)) abort(omni.api, "\"start.field.internal.omniscope\" is used internally by this block. The right input data cannot contain a field with this name.")
if ("end.field.internal.omniscope" %in% names(right)) abort(omni.api, "\"end.field.internal.omniscope\" is used internally by this block. The right input data cannot contain a field with this name.")

n <- unique(c(names(left), names(right)))


left.original <- data.frame(left)

left$value.field.internal.omniscope = left[, value.field]
right$start.field.internal.omniscope = right[, start.field]
right$end.field.internal.omniscope = right[, end.field]

if (has.eq.crit) {
	left$left.eq.field.internal.omniscope = left[, left.eq.field]
	right$right.eq.field.internal.omniscope = right[, right.eq.field]
}


if (has.eq.crit) {
	left <- left[complete.cases(left[, c(value.field, left.eq.field)]), ]
	right <- right[complete.cases(right[, c(start.field, end.field, right.eq.field)]), ]
} else {
	left <- left[complete.cases(left[, c(value.field)]), ]
	right <- right[complete.cases(right[, c(start.field, end.field)]), ]
}


is.date <- function(x) {class(x)[1] %in% c("POSIXct", "POSIXt")}

if (!is.numeric(left[, value.field]) && !is.date(left[, value.field])) abort(omni.api, "\"Value field\" must be numeric or date")
if (!is.numeric(right[, start.field]) && !is.date(right[, start.field])) abort(omni.api, "\"Interval start field\" must be numeric or date")
if (!is.numeric(right[, end.field]) && !is.date(right[, end.field])) abort(omni.api, "\"Interval end field\" must be numeric or date")



setDT(left)
setDT(right)


if (has.eq.crit) {
	join.on = c(paste("value.field.internal.omniscope", startComparator, "start.field.internal.omniscope", sep=""),
			paste("value.field.internal.omniscope", endComparator, "end.field.internal.omniscope", sep=""),
            paste("left.eq.field.internal.omniscope", "==", "right.eq.field.internal.omniscope"))


} else {
	join.on = c(paste("value.field.internal.omniscope", startComparator, "start.field.internal.omniscope", sep=""),
		paste("value.field.internal.omniscope", endComparator, "end.field.internal.omniscope", sep=""))
}




result <- left[right, on=join.on, allow.cartesian = T, nomatch=0, n, with=FALSE]

if (join.type == "LEFT") {
    left.merge <- merge.data.table(left.original, result, by = value.field, all.x = TRUE)
    left.missing <- left.merge[!complete.cases(left.merge[, c(start.field, end.field)]), ]
	result <- bind_rows(result, left.missing)
}

output.data <- result


if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)