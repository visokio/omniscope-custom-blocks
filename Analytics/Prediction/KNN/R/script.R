### Input fields

fields.to.use <- c("Field 1", "Field 2...")

field.to.predict <- "Field 3"

### Parameters

# whether to use all numeric fields to aid prediction
use.all.numeric.fields <- T

# whether to use the first categorical field to predict
use.first.categorical.field <- T

# The number of neighbours to use, the K in K-Nearest Neighbours
number.of.neighbours <- 5


### Script


library(class)

if (!exists("input.data"))
  stop("No input data")

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[sapply(input.data, is.numeric)]
}

if (use.first.categorical.field) {
  field.to.predict <- names(input.data)[sapply(input.data,is.factor)][1]
}


if (!exists("input.data.2"))  input.data.2 <- input.data

test <- input.data.2[,fields.to.use]

# Build the model
model <- knn(input.data[,fields.to.use], input.data.2[,fields.to.use], input.data[,field.to.predict], k=number.of.neighbours)

output.data <- cbind(input.data.2, model)
names(output.data) = c(names(input.data.2), paste0("Predicted (", field.to.predict, ")"))
