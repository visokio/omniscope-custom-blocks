library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

### Options

from.field <- get.option(omni.api, "from")
to.field <- get.option(omni.api, "to")
attribute.field <- get.option(omni.api, "category")

### Script

suppressPackageStartupMessages(library(data.table))

is.set <- function(x) !is.null(x) && length(x) == 1 && !is.na(x) && nzchar(x)

if (is.null(input.data)) abort(omni.api, "No input data: connect records with one connection each")
if (!is.set(from.field)) abort(omni.api, "Choose the From field")
if (!is.set(to.field)) abort(omni.api, "Choose the To field")
if (!is.set(attribute.field)) abort(omni.api, "Choose the Category field")
for (f in c(from.field, to.field, attribute.field)) {
  if (!(f %in% names(input.data))) abort(omni.api, paste0("Field not found in the input: ", f))
}

# Node names and categories are compared as text, so numeric IDs work too
as.text <- function(x) if (inherits(x, "POSIXct")) format(x, "%Y-%m-%d %H:%M:%S") else as.character(x)
connection.data <- data.table(from = as.text(input.data[[from.field]]), to = as.text(input.data[[to.field]]),
                              category = as.text(input.data[[attribute.field]]))
connection.data <- connection.data[!is.na(from) & !is.na(to) & !is.na(category)]

# Each category's connections share a weight of 1, so large categories don't outweigh small ones
connection.data[, sfreq := 1 / .N, by = category]
connection.data[, connections := .N, by = category]
connection.data.to <- connection.data[, .(sfreq = sum(sfreq)), by = .(to, category)]

# The mix of categories connected to each target node
connection.data.categories <- connection.data.to[, .(category = category, cfreq = sfreq / sum(sfreq)), by = to]

# For each category A and each target it connects to, the other categories at that target, rescaled to sum to 1
connection.cross <- merge(connection.data.to, connection.data.categories, by = "to", allow.cartesian = TRUE)
connection.cross.filtered <- connection.cross[category.x != category.y]
connection.cross.filtered[, cfreq := cfreq / sum(cfreq), by = .(category.x, to)]
connection.cross.prob <- connection.cross.filtered[, .(prob = sum(sfreq * cfreq)), by = .(category.x, category.y)]

counts <- unique(connection.data[, .(category, connections)])
connection.cross.prob <- merge(connection.cross.prob, counts, by.x = "category.x", by.y = "category", all.x = TRUE)
setorder(connection.cross.prob, category.x, -prob, category.y)

output.data <- data.frame(`From category` = as.character(connection.cross.prob$category.x),
                          `To category` = as.character(connection.cross.prob$category.y),
                          Probability = round(as.numeric(connection.cross.prob$prob), 10),
                          Connections = as.integer(connection.cross.prob$connections),
                          check.names = FALSE, stringsAsFactors = FALSE)

write.output.records(omni.api, output.data, output.number=1)
close(omni.api)
