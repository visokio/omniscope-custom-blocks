library(omniscope)

omniscope = Omniscope()

input.data = read.input.records(omniscope, input.number=1)

### Input fields
from.field <- get.option(omniscope, "from")

to.field <- get.option(omniscope, "to")

attribute.field <- get.option(omniscope, "category")

### Script


require(data.table)

# sanity checks
if (is.null(input.data)) stop("No input data")

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
  write.output.records(omniscope, data.frame(output.data), output.number=1)
}
close(omniscope)
