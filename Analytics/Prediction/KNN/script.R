library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
input.data.2 = read.input.records(omni.api, input.number=2)

### Input fields

fields.to.use <- get.option(omni.api, "fieldsToUse")

field.to.predict <- get.option(omni.api, "fieldToPredict")

### Parameters

# whether to use all numeric fields to aid prediction
use.all.numeric.fields <- get.option(omni.api, "useAllNumericFields")

# whether to use the first categorical field to predict
use.first.categorical.field <- get.option(omni.api, "predictFirstCategoricalField")

# The number of neighbours to use, the K in K-Nearest Neighbours
number.of.neighbours <- get.option(omni.api, "numberOfNeighbours")


### Script


library(class)

if (is.null(input.data))
  stop("No input data")

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[sapply(input.data, is.numeric)]
}

if (use.first.categorical.field) {
  field.to.predict <- names(input.data)[sapply(input.data,is.factor)][1]
}


if (is.null(input.data.2))  input.data.2 <- input.data

test <- input.data.2[,fields.to.use]

# Build the model
model <- knn(input.data[,fields.to.use], input.data.2[,fields.to.use], input.data[,field.to.predict], k=number.of.neighbours)

output.data <- cbind(input.data.2, model)
names(output.data) = c(names(input.data.2), paste0("Predicted (", field.to.predict, ")"))


if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)
