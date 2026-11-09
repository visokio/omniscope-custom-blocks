library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)
input.data.2 = read.input.records(omni.api, input.number=2)

### Options

fields.to.use <- get.option(omni.api, "fieldsToUse")
use.all.numeric.fields <- isTRUE(get.option(omni.api, "useAllNumericFields"))
max.clusters <- get.option(omni.api, "maxClusters")

### Script

suppressPackageStartupMessages(library(mclust))

if (is.null(input.data)) abort(omni.api, "No input data: connect records to the first input")

output.fields <- c("Cluster", "Cluster probability")
is.number.field <- function(x) is.numeric(x) && !inherits(x, c("POSIXct", "Date"))

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[vapply(input.data, is.number.field, TRUE)]
  fields.to.use <- setdiff(fields.to.use, output.fields)
  if (length(fields.to.use) == 0) abort(omni.api, "The input has no Integer or Decimal fields to cluster on")
} else {
  fields.to.use <- fields.to.use[!is.na(fields.to.use) & nzchar(fields.to.use)]
  if (length(fields.to.use) == 0) {
    abort(omni.api, "Choose the fields to cluster on, or tick \"Use all numeric fields\"")
  }
}

check.fields <- function(data, which.input) {
  missing.fields <- setdiff(fields.to.use, names(data))
  if (length(missing.fields)) {
    abort(omni.api, paste0("Field not found in the ", which.input, ": ", paste(missing.fields, collapse = ", ")))
  }
  not.numeric <- fields.to.use[!vapply(data[fields.to.use], is.number.field, TRUE)]
  if (length(not.numeric)) {
    abort(omni.api, paste0("Only Integer and Decimal fields can be clustered on; not in the ", which.input, ": ",
                           paste(not.numeric, collapse = ", ")))
  }
}
check.fields(input.data, "first input")
if (!is.null(input.data.2)) check.fields(input.data.2, "second input")

if (is.null(max.clusters) || is.na(max.clusters) || max.clusters < 1) {
  abort(omni.api, "\"Maximum number of clusters\" must be 1 or more")
}
max.clusters <- as.integer(max.clusters)

values.of <- function(data, rows) {
  m <- as.matrix(data[rows, fields.to.use, drop = FALSE])
  storage.mode(m) <- "double"
  m
}

# Records with a missing value in a chosen field are kept, with an empty Cluster and probability
complete <- complete.cases(input.data[fields.to.use])
values <- values.of(input.data, complete)

with.clusters <- function(data, cluster, probability) {
  data$Cluster <- cluster  # replaces existing fields of these names
  data$`Cluster probability` <- probability
  data
}

cluster <- rep(NA_integer_, nrow(input.data))
probability <- rep(NA_real_, nrow(input.data))
model <- NULL

if (nrow(values) > 0) {
  if (nrow(values) < 2) abort(omni.api, "At least 2 records with values in the chosen fields are needed")
  max.clusters <- min(max.clusters, nrow(unique(values)))

  # Above 2,000 records mclust starts from a random sample; a fixed seed keeps the result the same on every run
  set.seed(1)
  model <- Mclust(values, G = seq_len(max.clusters), verbose = FALSE)
  if (is.null(model)) {
    abort(omni.api, "No mixture model could be fitted to these fields (are the values all the same, or too few?)")
  }

  # Number the clusters in the order they first appear in the input, so the numbering is stable
  first.seen <- unique(model$classification)
  first.seen <- c(first.seen, setdiff(seq_len(model$G), first.seen))  # a component no record went to
  relabel <- function(k) match(k, first.seen)
  cluster[complete] <- relabel(model$classification)
  probability[complete] <- round(apply(model$z, 1, max), 6)
}

output.data <- with.clusters(input.data, cluster, probability)
write.output.records(omni.api, output.data, output.number=1)

if (!is.null(input.data.2)) {
  # Assign each record of the second input to the most probable cluster of the model fitted on the first
  complete.2 <- complete.cases(input.data.2[fields.to.use])
  cluster.2 <- rep(NA_integer_, nrow(input.data.2))
  probability.2 <- rep(NA_real_, nrow(input.data.2))
  if (any(complete.2) && !is.null(model)) {
    prediction <- predict(model, newdata = values.of(input.data.2, complete.2))
    cluster.2[complete.2] <- relabel(prediction$classification)
    probability.2[complete.2] <- round(apply(prediction$z, 1, max), 6)
  }
  write.output.records(omni.api, with.clusters(input.data.2, cluster.2, probability.2), output.number=2)
}

close(omni.api)
