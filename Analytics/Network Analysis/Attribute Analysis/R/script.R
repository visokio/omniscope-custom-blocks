### Input fields
from.field <- "From field"

to.field <- "To field"

attribute.field <- "Category field"

### Script


require(data.table)

# sanity checks
if (!exists("input.data")) stop("No input data")

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
