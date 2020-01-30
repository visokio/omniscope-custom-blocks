library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
input.data.2 = read.input.records(omni.api, input.number=2)

### Input fields

fields.to.use <- get.option(omni.api, "fieldsToUse")

### Parameters

use.all.numeric.fields <- get.option(omni.api, "useAllNumericFields")

num.clusters <- get.option(omni.api, "numClusters")

### Script


if (is.null(input.data)) abort(omni.api, "No input data")

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[sapply(input.data, is.numeric)]
}

# Create a matrix of the numeric fields

if (!all(sapply(input.data[,fields.to.use], is.numeric))) abort(omni.api, "Only numeric fields in \"Fields to use\" are supported")

input.data <- input.data[complete.cases(input.data[, fields.to.use]), ]


original.data.matrix <- as.matrix(input.data[, fields.to.use])

# Do the clustering
cluster.results <- kmeans(original.data.matrix, num.clusters)

output.data <- cbind(input.data, cluster.results$cluster)
names(output.data) <- c(names(input.data), "Cluster")


if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}

close(omni.api)
