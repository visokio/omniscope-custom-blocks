library(omniscope.api)
library(data.table)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
fields = get.option(omni.api, "fields")

setDT(input.data)

for (field in fields) {

field.max = max(input.data[, field, with=F])
field.min = min(input.data[, field, with=F])

input.data[, (field) := (get(field)-field.min) / (field.max - field.min)]

}

output.data = input.data
if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)