library(omniscope.api)
library(data.table)

omni.api = omniscope.api()


left = read.input.records(omni.api, input.number=1)
right = read.input.records(omni.api, input.number=2)

left.field = get.option(omni.api, "left")
comparator = get.option(omni.api, "comparator")
right.field = get.option(omni.api, "right")

#sanity checks
if (is.null(left)) {
  cancel(omni.api, "No 'left' input data")
  stop()
}
if (is.null(right)) {
  cancel(omni.api, "No 'right' input data")
  stop()
}

if (!is.numeric(left[, left.field])) {
  cancel(omni.api, "\"Left field\" must be numeric")
  stop()
}

if (!is.numeric(right[, right.field])) {
  cancel(omni.api, "\"Right field\" must be numeric")
  stop()
}

if ("left.field.internal.omniscope" %in% names(left)) {
  cancel(omni.api, "\"left.field.internal.omniscope\" is used internally by this block. The left input data cannot contain a field with this name.")
  stop()
}

if ("right.field.internal.omniscope" %in% names(right)) {
  cancel(omni.api, "\"right.field.internal.omniscope\" is used internally by this block. The right input data cannot contain a field with this name.")
  stop()
}


left <- left[complete.cases(left[, left.field]), ]
right <- right[complete.cases(right[, right.field]), ]

setDT(left)
setDT(right)

setnames(left, left.field, "left.field.internal.omniscope")
setnames(right, right.field, "right.field.internal.omniscope")

ex = str2lang(paste("left.field.internal.omniscope", comparator, "right.field.internal.omniscope", sep=" "))

join.on = substitute(list(ex), list(ex = ex))

output.data <- data.frame(left[right, on = eval(join.on), allow.cartesian = T, nomatch=0])

setnames(output.data, "left.field.internal.omniscope", left.field)

if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)
