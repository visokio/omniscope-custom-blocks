library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
input.data.2 = read.input.records(omni.api, input.number=2)

if(is.null(input.data)) abort(omni.api, "You have to provide a list of fields to be renamed in the first input")
if(is.null(input.data.2)) abort(omni.api, "You have to provide a data set in the second input")

current.names.field = get.option(omni.api, "currentNames")
current.names = input.data[, current.names.field]
if (length(current.names) !=length(unique(current.names))) abort(omni.api, "\"Current names\" contains duplicates")


new.names.field = get.option(omni.api, "newNames")
new.names = input.data[, new.names.field]

old.names = names(input.data.2)

unused.names = data.frame(unused = setdiff(current.names, old.names))
unchanged.names = data.frame(unchanged = setdiff(old.names, current.names))

library(data.table)
setDT(input.data.2)

setnames(input.data.2, current.names, new.names, skip_absent=TRUE)

output.data = input.data.2
if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
  write.output.records(omni.api, unused.names, output.number=2)
  write.output.records(omni.api, unchanged.names, output.number=3)
}
close(omni.api)