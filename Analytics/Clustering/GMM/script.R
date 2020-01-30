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

if (is.null(input.data)) abort(omni.api, "No input data")

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[sapply(input.data, is.numeric)]
}

if (!all(sapply(input.data[,fields.to.use], is.numeric))) abort(omni.api, "Only numeric fields in \"Fields to use\" are supported")

input.data <- input.data[complete.cases(input.data[, fields.to.use]), ]

# Calculate the clustering
model <- Mclust(input.data[,fields.to.use])

output.data <- cbind(input.data, model$classification)
names(output.data) <- c(names(input.data), "Cluster")

if (!is.null(input.data.2)) {

  # sanity checks to ensure the second input data is compatible with the first
  if (!all(fields.to.use %in% names(input.data.2))) abort(omni.api, "Not all fields in \"Fields to use\" are present in the second input data")
  if (!all(sapply(input.data.2[,fields.to.use], is.numeric))) abort(omni.api, "Only numeric fields in \"Fields to use\" are supported in the second input data")


  input.data.2 <- input.data.2[complete.cases(input.data.2[, fields.to.use]), ]

  # Cluster the unseen data
  new.assignments <- predict(model, newdata=input.data.2[, fields.to.use])$classification

  output.data.2 <- cbind(input.data.2, new.assignments)
  names(output.data) <- c(names(input.data.2), "Cluster")

}

if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
if (exists("output.data.2") && !is.null(output.data.2)) {
  write.output.records(omni.api, output.data.2, output.number=2)
}
close(omni.api)
