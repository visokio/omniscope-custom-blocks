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

if (is.null(input.data)) {
  cancel(omni.api, "No input data")
  stop()
}

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[sapply(input.data, is.numeric)]
}

if (use.first.categorical.field) {
  field.to.predict <- names(input.data)[sapply(input.data,is.character)][1]
}

if (!all(sapply(input.data[,fields.to.use], is.numeric))) {
  cancel(omni.api, "Only numeric fields in \"Fields to use\" are supported")
  stop()
}

if (!is.numeric(input.data[, field.to.predict])) {
  cancel(omni.api, "\"Field to predict\" must be numeric")
  stop()
}

input.data <- input.data[complete.cases(input.data[, fields.to.use]), ]

if (is.null(input.data.2))  {
  input.data.2 <- input.data
} else {

  if (!all(fields.to.use %in% names(input.data.2))) {
    cancel(omni.api, "Not all fields in \"Fields to use\" are present in the second input data")
    stop()
  }

  if (!all(sapply(input.data.2[,fields.to.use], is.numeric))) {
    cancel(omni.api, "Only numeric fields in \"Fields to use\" are supported in the second input data")
    stop()
  }

  input.data.2 <- input.data.2[complete.cases(input.data.2[, fields.to.use]), ]

}



# Build the model
model <- knn(input.data[,fields.to.use], input.data.2[,fields.to.use], input.data[,field.to.predict], k=number.of.neighbours)

output.data <- cbind(input.data.2, model)
names(output.data) = c(names(input.data.2), paste0("Predicted (", field.to.predict, ")"))


if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)
