library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

### Options

fields.to.use <- get.option(omni.api, "fieldsToUse")
use.all.numeric.fields <- isTRUE(get.option(omni.api, "useAllNumericFields"))
num.clusters <- get.option(omni.api, "numClusters")
standardise <- isTRUE(get.option(omni.api, "standardise"))

### Script

if (is.null(input.data)) abort(omni.api, "No input data: connect records to the first input")

is.number.field <- function(x) is.numeric(x) && !inherits(x, c("POSIXct", "Date"))

if (use.all.numeric.fields) {
  fields.to.use <- names(input.data)[vapply(input.data, is.number.field, TRUE)]
  fields.to.use <- setdiff(fields.to.use, "Cluster")
  if (length(fields.to.use) == 0) abort(omni.api, "The input has no Integer or Decimal fields to cluster on")
} else {
  fields.to.use <- fields.to.use[!is.na(fields.to.use) & nzchar(fields.to.use)]
  if (length(fields.to.use) == 0) {
    abort(omni.api, "Choose the fields to cluster on, or tick \"Use all numeric fields\"")
  }
  missing.fields <- setdiff(fields.to.use, names(input.data))
  if (length(missing.fields)) {
    abort(omni.api, paste0("Field not found in the input: ", paste(missing.fields, collapse = ", ")))
  }
  not.numeric <- fields.to.use[!vapply(input.data[fields.to.use], is.number.field, TRUE)]
  if (length(not.numeric)) {
    abort(omni.api, paste0("Only Integer and Decimal fields can be clustered on: ",
                           paste(not.numeric, collapse = ", ")))
  }
}

if (is.null(num.clusters) || is.na(num.clusters) || num.clusters < 1) {
  abort(omni.api, "\"Number of clusters\" must be 1 or more")
}
num.clusters <- as.integer(num.clusters)

# Records with a missing value in a chosen field are kept, with an empty Cluster
complete <- complete.cases(input.data[fields.to.use])
values <- as.matrix(input.data[complete, fields.to.use, drop = FALSE])
storage.mode(values) <- "double"

cluster <- rep(NA_integer_, nrow(input.data))

if (nrow(values) > 0) {
  if (standardise) {
    centre <- colMeans(values)
    spread <- apply(values, 2, sd)
    spread[is.na(spread) | spread == 0] <- 1  # a constant field (or a single record) adds nothing
    values <- sweep(sweep(values, 2, centre), 2, spread, "/")
  }

  distinct.points <- nrow(unique(values))
  if (num.clusters > distinct.points) {
    abort(omni.api, paste0("\"Number of clusters\" is ", num.clusters, " but the records have only ",
                           distinct.points, " distinct combination(s) of values in the chosen fields"))
  }

  # A fixed seed and 10 random starts: the same input gives the same clusters on every run
  set.seed(1)
  # On large inputs R can warn that its fine-tuning stage stopped early; the clusters are still complete
  result <- withCallingHandlers(
    kmeans(values, centers = num.clusters, nstart = 10, iter.max = 100),
    warning = function(w) {
      if (grepl("Quick-TRANSfer", conditionMessage(w))) invokeRestart("muffleWarning")
    })

  # Number the clusters in the order they first appear in the input, so the numbering is stable
  first.seen <- unique(result$cluster)
  cluster[complete] <- match(result$cluster, first.seen)
}

output.data <- input.data
output.data$Cluster <- cluster  # replaces an existing Cluster field

write.output.records(omni.api, output.data, output.number=1)
close(omni.api)
