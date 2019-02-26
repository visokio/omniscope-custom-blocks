### Input fields

fields.to.use <- c("Field 1", "Field 2...")

### Parameters

use.all.numeric.fields <- F

### Script


library(mclust)

if (!exists("input.data"))
  stop("No input data")

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[sapply(input.data, is.numeric)]
}

# Calculate the clustering
model <- Mclust(input.data[,fields.to.use])

output.data <- cbind(input.data, model$classification)
names(output.data) <- c(names(input.data), "Cluster")

if (exists("input.data.2")) {
  
  # Cluster the unseen data
  new.data.to.cluster <- input.data.2[,fields.to.use]
  new.assignments <- predict(model, newdata=new.data.to.cluster)$classification
  
  output.data.2 <- cbind(input.data.2, new.assignments)
  names(output.data) <- c(names(input.data), "Cluster")
  
}