library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
input.data.2 = read.input.records(omni.api, input.number=2)

### Options

fields.to.use <- get.option(omni.api, "fieldsToUse")
field.to.predict <- get.option(omni.api, "fieldToPredict")
use.all.numeric.fields <- isTRUE(get.option(omni.api, "useAllNumericFields"))
number.of.neighbours <- get.option(omni.api, "numberOfNeighbours")
standardise <- isTRUE(get.option(omni.api, "standardise"))

### Script

library(class)

if (is.null(input.data)) abort(omni.api, "No input data: connect the records with known values to the first input")

if (is.null(field.to.predict) || is.na(field.to.predict) || !nzchar(field.to.predict)) {
  abort(omni.api, "Choose the field to predict")
}
if (!(field.to.predict %in% names(input.data))) {
  abort(omni.api, paste0("Field to predict not found in the first input: ", field.to.predict))
}
if (!is.character(input.data[[field.to.predict]])) {
  abort(omni.api, paste0("The field to predict must be a Text field (a category): ", field.to.predict))
}

predicted.field <- paste0("Predicted (", field.to.predict, ")")
share.field <- "Vote share"
is.number.field <- function(x) is.numeric(x) && !inherits(x, c("POSIXct", "Date"))

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[vapply(input.data, is.number.field, TRUE)]
  fields.to.use <- setdiff(fields.to.use, c(field.to.predict, predicted.field, share.field))
  if (length(fields.to.use) == 0) abort(omni.api, "The first input has no Integer or Decimal fields to predict from")
} else {
  fields.to.use <- fields.to.use[!is.na(fields.to.use) & nzchar(fields.to.use)]
  if (length(fields.to.use) == 0) {
    abort(omni.api, "Choose the fields to predict from, or tick \"Use all numeric fields\"")
  }
}

check.fields <- function(data, which.input) {
  missing.fields <- setdiff(fields.to.use, names(data))
  if (length(missing.fields)) {
    abort(omni.api, paste0("Field not found in the ", which.input, ": ", paste(missing.fields, collapse = ", ")))
  }
  not.numeric <- fields.to.use[!vapply(data[fields.to.use], is.number.field, TRUE)]
  if (length(not.numeric)) {
    abort(omni.api, paste0("Only Integer and Decimal fields can be used to predict from; not in the ", which.input,
                           ": ", paste(not.numeric, collapse = ", ")))
  }
}
check.fields(input.data, "first input")
if (!is.null(input.data.2)) check.fields(input.data.2, "second input")

if (is.null(number.of.neighbours) || is.na(number.of.neighbours) || number.of.neighbours < 1) {
  abort(omni.api, "\"Number of neighbours\" must be 1 or more")
}
k <- as.integer(number.of.neighbours)

values.of <- function(data, rows) {
  m <- as.matrix(data[rows, fields.to.use, drop = FALSE])
  storage.mode(m) <- "double"
  m
}

# Training records: those with a known value to predict and values in every chosen field
complete.1 <- complete.cases(input.data[fields.to.use])
known <- complete.1 & !is.na(input.data[[field.to.predict]])
train <- values.of(input.data, known)
classes <- factor(input.data[[field.to.predict]][known])

target <- if (is.null(input.data.2)) input.data else input.data.2
complete.t <- complete.cases(target[fields.to.use])
predicted <- rep(NA_character_, nrow(target))
share <- rep(NA_real_, nrow(target))

if (any(complete.t)) {
  if (nrow(train) == 0) {
    abort(omni.api, paste0("No records in the first input have a known ", field.to.predict,
                           " and values in every field to predict from"))
  }
  if (k >= nrow(train)) {
    abort(omni.api, paste0("\"Number of neighbours\" (", k, ") must be less than the number of records with a known ",
                           field.to.predict, " (", nrow(train), ")"))
  }

  if (standardise) {
    centre <- colMeans(train)
    spread <- apply(train, 2, sd)
    spread[is.na(spread) | spread == 0] <- 1  # a constant field adds nothing
    scale.values <- function(m) sweep(sweep(m, 2, centre), 2, spread, "/")
  } else {
    scale.values <- function(m) m
  }

  # Ties between classes, or between equally distant neighbours, are broken at random: a fixed seed
  # gives the same predictions on every run
  set.seed(1)
  if (is.null(input.data.2)) {
    # One input: records with a known value are predicted from the others (leave one out), so the
    # prediction never includes the record's own value; records without one are predicted from all
    rows.known <- which(known)
    loo <- knn.cv(scale.values(train), classes, k = k, prob = TRUE)
    predicted[rows.known] <- as.character(loo)
    share[rows.known] <- attr(loo, "prob")
    rows.new <- which(complete.t & !known)
    if (length(rows.new)) {
      fit <- knn(scale.values(train), scale.values(values.of(target, rows.new)), classes, k = k, prob = TRUE)
      predicted[rows.new] <- as.character(fit)
      share[rows.new] <- attr(fit, "prob")
    }
  } else {
    rows.new <- which(complete.t)
    fit <- knn(scale.values(train), scale.values(values.of(target, rows.new)), classes, k = k, prob = TRUE)
    predicted[rows.new] <- as.character(fit)
    share[rows.new] <- attr(fit, "prob")
  }
}

output.data <- target
output.data[[predicted.field]] <- predicted  # replaces existing fields of these names
output.data[[share.field]] <- round(share, 6)

write.output.records(omni.api, output.data, output.number=1)
close(omni.api)
