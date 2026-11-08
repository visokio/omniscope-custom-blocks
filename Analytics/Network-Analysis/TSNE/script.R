library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

### Options

from.field <- get.option(omni.api, "from")
to.field <- get.option(omni.api, "to")
weight.field <- get.option(omni.api, "weight")  # optional

# number of output dimensions (1 to 3)
output.dimensions <- get.option(omni.api, "outputDimensions")
# t-SNE first reduces each node's connection profile to this many dimensions with PCA
initial.dimensions <- get.option(omni.api, "initialDimensions")
# roughly how many neighbours each node takes into account; lower values stress local structure
perplexity <- get.option(omni.api, "perplexity")

### Script

suppressPackageStartupMessages({
  library(data.table)
  library(Rtsne)
})

is.set <- function(x) !is.null(x) && length(x) == 1 && !is.na(x) && nzchar(x)
is.number.field <- function(x) is.numeric(x) && !inherits(x, c("POSIXct", "Date"))

if (is.null(input.data)) abort(omni.api, "No input data: connect records with one connection each")
if (!is.set(from.field)) abort(omni.api, "Choose the From field")
if (!is.set(to.field)) abort(omni.api, "Choose the To field")
has.weight <- is.set(weight.field)
for (f in c(from.field, to.field, if (has.weight) weight.field)) {
  if (!(f %in% names(input.data))) abort(omni.api, paste0("Field not found in the input: ", f))
}
if (has.weight && !is.number.field(input.data[[weight.field]])) {
  abort(omni.api, paste0("The Weight field must be numeric: ", weight.field))
}
if (!(output.dimensions %in% 1:3)) abort(omni.api, "\"Number of output dimensions\" must be 1, 2 or 3")
if (is.null(initial.dimensions) || is.na(initial.dimensions) || initial.dimensions < 1) {
  abort(omni.api, "\"PCA dimensions\" must be 1 or more")
}
if (is.null(perplexity) || is.na(perplexity) || perplexity <= 0) abort(omni.api, "\"Perplexity\" must be more than 0")

# Node names are compared as text, so numeric IDs work too
as.text <- function(x) if (inherits(x, "POSIXct")) format(x, "%Y-%m-%d %H:%M:%S") else as.character(x)
connection.data <- data.table(from = as.text(input.data[[from.field]]), to = as.text(input.data[[to.field]]),
                              weight = if (has.weight) as.numeric(input.data[[weight.field]]) else 1)
connection.data <- connection.data[!is.na(from) & !is.na(to) & !is.na(weight)]
if (any(connection.data$weight < 0)) abort(omni.api, "The Weight field has negative values")

# One index per node, in order of first appearance
nodes <- data.table(node = unique(c(rbind(connection.data$from, connection.data$to))))
nodes[, i := .I]
degree <- table(c(connection.data$from, connection.data$to))
nodes[, connections := as.integer(degree[node])]

output.names <- c("Node", paste("Dimension", seq_len(output.dimensions)), "Connections")
n <- nrow(nodes)

if (n == 0) {
  output.data <- as.data.frame(setNames(c(list(character(0)), rep(list(numeric(0)), output.dimensions),
                                          list(integer(0))), output.names), check.names = FALSE)
} else {
  if (n - 1 < 3 * perplexity) {
    abort(omni.api, paste0("\"Perplexity\" is too large for ", n, " nodes: use at most ", floor((n - 1) / 3),
                           ", or more data (t-SNE needs at least 3 x perplexity + 1 nodes)"))
  }

  # Adjacency matrix: each node's row holds its connection weights to every node, both directions,
  # with repeated connections between the same two nodes added up
  links <- connection.data[, .(weight = sum(weight)),
                           by = .(src = nodes$i[match(from, nodes$node)], dst = nodes$i[match(to, nodes$node)])]
  adjacency.matrix <- matrix(0, n, n)
  adjacency.matrix[cbind(links$src, links$dst)] <- links$weight
  adjacency.matrix <- adjacency.matrix + t(adjacency.matrix)

  # t-SNE starts from random positions: a fixed seed gives the same map on every run
  set.seed(1)
  tsne <- Rtsne(adjacency.matrix, dims = output.dimensions, initial_dims = initial.dimensions,
                perplexity = perplexity, check_duplicates = FALSE, max_iter = 10000)

  output.data <- data.frame(nodes$node, round(tsne$Y, 6), nodes$connections, stringsAsFactors = FALSE)
  names(output.data) <- output.names
}

write.output.records(omni.api, output.data, output.number=1)
close(omni.api)
