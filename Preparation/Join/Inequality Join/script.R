library(omniscope)
library(data.table)

omniscope = Omniscope()


left = read.input.records(omniscope, input.number=1)
if (is.null(left)) stop("No 'left' input data")
setDT(left)

right = read.input.records(omniscope, input.number=2)
if (is.null(right)) stop("No 'right' input data")
setDT(right)

left.field = get.option(omniscope, "left")
comparator = get.option(omniscope, "comparator")
right.field = get.option(omniscope, "right")

ex = str2lang(paste(left.field, comparator, right.field, sep=" "))

join.on = substitute(list(ex), list(ex = ex))

output.data <- data.frame(left[right, on = eval(join.on), allow.cartesian = T, nomatch=0])


if (!is.null(output.data)) {
  write.output.records(omniscope, output.data, output.number=1)
}
close(omniscope)