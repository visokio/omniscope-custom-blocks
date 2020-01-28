library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

### Input fields
from.field <- get.option(omni.api, "from")

to.field <- get.option(omni.api, "to")

attribute.field <- get.option(omni.api, "category")

### Script


require(data.table)

# sanity checks
if (is.null(input.data)) {
  cancel(omni.api, "No input data")
  stop()
}

if (!is.character(input.data[, from.field])) {
  cancel(omni.api, "\"From field\" must be of type text")
  stop()
}

if (!is.character(input.data[, to.field])) {
  cancel(omni.api, "\"To field\" must be of type text")
  stop()
}

if (!is.character(input.data[, attribute.field])) {
  cancel(omni.api, "\"Attribute field\" must be of type text")
  stop()
}

input.fields = c(from.field, to.field, attribute.field)

input.data <- input.data[complete.cases(input.data[, input.fields]), ]

connection.data <- data.table(from=input.data[, from.field], to=input.data[, to.field], category=input.data[, attribute.field])
connection.data[,sfreq:=1/.N, by=category]
connection.data.to <- connection.data[,.(sfreq=sum(sfreq)), by=.(to, category)]

connection.data.categories <- connection.data.to[,.(category=category, cfreq=sfreq/sum(sfreq)),by=to]

connection.cross <- merge(connection.data.to, connection.data.categories, by="to", allow.cartesian=TRUE)
connection.cross.filtered <- connection.cross[category.x != category.y]
connection.cross.filtered[, cfreq:=cfreq/sum(cfreq), by=.(category.x, to)]
connection.cross.prob <- connection.cross.filtered[, .(prob=sum(sfreq * cfreq)), by=.(category.x, category.y)]
setnames(connection.cross.prob, c("from", "to", "probability"))
output.data <- connection.cross.prob


if (!is.null(output.data)) {
  write.output.records(omni.api, data.frame(output.data), output.number=1)
}
close(omni.api)
