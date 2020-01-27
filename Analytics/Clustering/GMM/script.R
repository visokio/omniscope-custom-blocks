library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
input.data.2 = read.input.records(omni.api, input.number=2)

### Input fields

fields.to.use <- get.option(omni.api, "fieldsToUse")

### Parameters

use.all.numeric.fields <- get.option(omni.api, "useAllNumericFields")

### Script


library(mclust)

if (is.null(input.data))
  stop("No input data")

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[sapply(input.data, is.numeric)]
}

# Calculate the clustering
model <- Mclust(input.data[,fields.to.use])

output.data <- cbind(input.data, model$classification)
names(output.data) <- c(names(input.data), "Cluster")

if (!is.null(input.data.2)) {

  # Cluster the unseen data
  new.data.to.cluster <- input.data.2[,fields.to.use]
  new.assignments <- predict(model, newdata=new.data.to.cluster)$classification

  output.data.2 <- cbind(input.data.2, new.assignments)
  names(output.data) <- c(names(input.data), "Cluster")

}

if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
if (exists("output.data.2") && !is.null(output.data.2)) {
  write.output.records(omni.api, output.data.2, output.number=2)
}
close(omni.api)
