library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

### Input fields
from.field <- get.option(omni.api, "from")

to.field <- get.option(omni.api, "to")

# this is optional and can also be NULL
weight.field <- get.option(omni.api, "weight")

### Parameters

# number of output dimensions in the data
output.dimensions <- get.option(omni.api, "outputDimensions")

# an initial step in tsne is a dimensionality reduction via PCA. This variable specifies to how many initial dimensions the network should be reduced
initial.dimensions <- get.option(omni.api, "initialDimensions")

# specifies more or less how many neighbour points each data point sees. The lower the more local relationships are accentuated
perplexity <- get.option(omni.api, "perplexity")

### Script


library(data.table)
library(Rtsne)

# sanity checks
if (is.null(input.data)) abort(omni.api, "No input data")
if (!is.character(input.data[, from.field])) abort(omni.api, "\"From field\" must be of type text")
if (!is.character(input.data[, to.field])) abort(omni.api, "\"To field\" must be of type text")

has.weight = !is.null(weight.field)

if (has.weight && !is.numeric(input.data[, weight.field])) abort(omni.api, "\"Weight field\" must be numeric")


input.fields = c(from.field, to.field)
if (has.weight) input.fields <- c(input.fields, weight.field)

input.data <- input.data[complete.cases(input.data[, input.fields]), ]


# extract network
if (has.weight) {
  connection.data <- data.table(from=input.data[, from.field], to=input.data[, to.field], weight=input.data[, weight.field])
} else {
  connection.data <- data.table(from=input.data[, from.field], to=input.data[, to.field], weight=1)
}

# assign a consecutive index to each node
nodes.from <- connection.data[,.N,by=from]
setnames(nodes.from, c("node","n"))
nodes.to <- connection.data[,.N,by=to]
setnames(nodes.to, c("node", "n"))
nodes <- rbind(nodes.from, nodes.to)
nodes <- nodes[,.(n=sum(n)), by=node]
nodes[, n:=NULL]
nodes$i <- 1:nrow(nodes)

# use the consecutive indexes to refer to nodes in the network
links <- merge(connection.data, nodes, by.x = "from", by.y="node")
links <- merge(links, nodes, by.x = "to", by.y="node")

# create adjacency matrix
indexes <- links[, .(i.x, i.y, weight)]
edges <- as.matrix(indexes[, 1:2])
adjacency.matrix <- matrix(0, nrow(nodes), nrow(nodes))
adjacency.matrix[edges]<- indexes$weight

# perform tsne
tsne <- Rtsne(adjacency.matrix, dims = output.dimensions, initial_dims = initial.dimensions, perplexity = perplexity, check_duplicates = FALSE,  max_iter = 10000)

ts# extract x,y coordinates
y <- as.data.table(tsne$Y)
y$i <- 1:nrow(y)
output.data <- merge(nodes, y, by.x="i", by.y="i")
output.data[,i:=NULL]


if (!is.null(output.data)) {
  write.output.records(omni.api, data.frame(output.data), output.number=1)
}
close(omni.api)
