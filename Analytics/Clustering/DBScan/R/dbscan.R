### Input fields

fields.to.use <- c("Field 1", "Field 2...")

### Parameters

use.all.numeric.fields <- F

### Script

library(dbscan)

if (!exists("input.data"))
  stop("No input data")

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[sapply(input.data, is.numeric)]
}

# Create a matrix of the numeric fields
original.data.matrix <- as.matrix(input.data[,fields.to.use])

# Set the epsilon value for DBSCAN
epsilon <- 1
# Set the minimum number of points in a single cluster
min.points <- 5

# Do the clustering
cluster.results <- dbscan(original.data.matrix, eps=epsilon)

output.data <- cbind(input.data, cluster.results$cluster)
names(output.data) <- c(names(input.data), "Cluster")

if (exists("input.data.2")) {
  
  # Create a matrix of the relevant fields
  new.data.matrix <- as.matrix(input.data.2[,fields.to.use])
  
  # Predict the cluster assigments of the new/unseen data
  new.data.prediction <- predict(cluster.results, new.data.matrix, data=original.data.matrix)
  
  output.data.2 <- cbind(input.data.2, new.data.prediction)
  names(output.data.2) <- c(names(input.data.2), "Cluster")
  
}