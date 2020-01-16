library(omniscope)

omniscope = Omniscope()

input.data = read.input.records(omniscope, input.number=1)
input.data.2 = read.input.records(omniscope, input.number=2)

### Input fields

fields.to.use <- get.option(omniscope, "fieldsToUse")

### Parameters

use.all.numeric.fields <- get.option(omniscope, "useAllNumericFields")

num.clusters <- get.option(omniscope, "numClusters")

### Script


if (is.null(input.data))
  stop("No input data")

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[sapply(input.data, is.numeric)]
}

# Create a matrix of the numeric fields
original.data.matrix <- as.matrix(input.data[,fields.to.use])

# Do the clustering
cluster.results <- kmeans(original.data.matrix, num.clusters)

output.data <- cbind(input.data, cluster.results$cluster)
names(output.data) <- c(names(input.data), "Cluster")

if (!is.null(input.data.2)) {

  # Create a matrix of the relevant fields
  new.data.matrix <- as.matrix(input.data.2[,fields.to.use])

  # Predict the cluster assigments of the new/unseen data
  new.data.prediction <- predict(cluster.results, new.data.matrix, data=original.data.matrix)

  output.data.2 <- cbind(input.data.2, new.data.prediction)
  names(output.data.2) <- c(names(input.data.2), "Cluster")

}


if (!is.null(output.data)) {
  write.output.records(omniscope, output.data, output.number=1)
}
if (exists("output.data.2") && !is.null(output.data.2)) {
  write.output.records(omniscope, output.data.2, output.number=2)
}
close(omniscope)
