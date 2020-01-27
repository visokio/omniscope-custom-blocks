library(omniscope.api)
library(data.table)

omni.api = omniscope.api()


left = read.input.records(omni.api, input.number=1)
if (is.null(left)) stop("No 'left' input data")
setDT(left)

right = read.input.records(omni.api, input.number=2)
if (is.null(right)) stop("No 'right' input data")
setDT(right)

left.field = get.option(omni.api, "left")
comparator = get.option(omni.api, "comparator")
right.field = get.option(omni.api, "right")

ex = str2lang(paste(left.field, comparator, right.field, sep=" "))

join.on = substitute(list(ex), list(ex = ex))

output.data <- data.frame(left[right, on = eval(join.on), allow.cartesian = T, nomatch=0])


if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)