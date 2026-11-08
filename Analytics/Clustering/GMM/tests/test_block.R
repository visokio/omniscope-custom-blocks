# Unit tests for the Gaussian Mixture Model block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Analytics/Clustering/GMM
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

readings <- file.path(BLOCK_DIR, "sample-data", "pump-readings.csv")
new.readings <- file.path(BLOCK_DIR, "sample-data", "new-readings.csv")
modes <- read.csv(file.path(BLOCK_DIR, "tests", "pump-modes.csv"), stringsAsFactors = FALSE)

run <- function(inputs, ...) run_block(BLOCK_DIR, inputs, list(...))
mode.of <- function(reading) modes$Mode[match(reading, modes$Reading)]

test_that("the sample's three operating modes come out as three clusters", {
  out <- expect_committed(run(list(readings)))$outputs[[1]]
  expect_equal(nrow(out), 150)
  expect_equal(names(out), c("Reading", "Time", "Temperature", "Vibration", "Cluster", "Cluster probability"))
  expect_true(is.integer(out$Cluster))
  expect_equal(as.vector(table(out$Cluster)), c(61, 49, 39))
  tab <- table(out$Cluster, mode.of(out$Reading))
  expect_equal(tab["1", "Normal"], 60)
  expect_equal(tab["2", "Idle"], 49)
  expect_equal(tab["3", "Heavy"], 39)
  expect_equal(sum(diag(tab[, c("Normal", "Idle", "Heavy")])), 148)  # one Heavy reading sits in Normal's cloud
  expect_true(all(out$`Cluster probability` >= 0 & out$`Cluster probability` <= 1, na.rm = TRUE))
  expect_gt(mean(out$`Cluster probability` > 0.9, na.rm = TRUE), 0.9)
})

test_that("a second input is assigned to the clusters found in the first", {
  # the original wrote the second output with a field called new.assignments, and gave the first
  # output the second input's field names
  res <- expect_committed(run(list(readings, new.readings)))
  first <- res$outputs[[1]]
  out <- res$outputs[[2]]
  expect_equal(names(first), c("Reading", "Time", "Temperature", "Vibration", "Cluster", "Cluster probability"))
  expect_equal(nrow(out), 12)
  expect_equal(names(out), c("Reading", "Time", "Temperature", "Vibration", "Cluster", "Cluster probability"))
  cluster.mode <- c("1" = "Normal", "2" = "Idle", "3" = "Heavy")
  expect_equal(unname(cluster.mode[as.character(out$Cluster)]), mode.of(out$Reading))
})

test_that("a second input with other fields as well works", {
  extra <- read.csv(new.readings, stringsAsFactors = FALSE)
  extra$Operator <- "AB"
  res <- expect_committed(run(list(readings, extra)))
  expect_equal(names(res$outputs[[1]])[1:4], c("Reading", "Time", "Temperature", "Vibration"))
  expect_equal(names(res$outputs[[2]]), c(names(extra), "Cluster", "Cluster probability"))
})

test_that("records with a missing value keep their place, with empty cluster fields", {
  out <- expect_committed(run(list(readings)))$outputs[[1]]
  expect_equal(out$Reading, sprintf("R-%04d", 1:150))
  expect_true(is.na(out$Cluster[23]))
  expect_true(is.na(out$`Cluster probability`[23]))
  new <- read.csv(new.readings, stringsAsFactors = FALSE)
  new$Temperature[2] <- NA
  out2 <- expect_committed(run(list(readings, new)))$outputs[[2]]
  expect_equal(nrow(out2), 12)
  expect_true(is.na(out2$Cluster[2]))
})

test_that("the same input gives the same clusters, also above 2,000 records", {
  set.seed(5)
  n <- 3000
  df <- data.frame(A = c(rnorm(n / 2, 0), rnorm(n / 2, 6)), B = rnorm(n))
  a <- expect_committed(run(list(df), maxClusters = 3))$outputs[[1]]
  runif(3)
  b <- expect_committed(run(list(df), maxClusters = 3))$outputs[[1]]
  expect_identical(a$Cluster, b$Cluster)
  expect_identical(a$`Cluster probability`, b$`Cluster probability`)
})

test_that("Maximum number of clusters caps the clusters, and chosen fields are used", {
  out <- expect_committed(run(list(readings), maxClusters = 2))$outputs[[1]]
  expect_lte(max(out$Cluster, na.rm = TRUE), 2)
  set.seed(2)
  df <- data.frame(Name = paste0("n", 1:40), A = c(rnorm(20, 0), rnorm(20, 10)), B = runif(40, 0, 100))
  out <- expect_committed(run(list(df), useAllNumericFields = FALSE, fieldsToUse = "A"))$outputs[[1]]
  expect_equal(out$Cluster, rep(1:2, each = 20))
})

test_that("existing Cluster fields are replaced and not clustered on", {
  df <- data.frame(A = c(rnorm(10, 0, 0.1), rnorm(10, 5, 0.1)), Cluster = 7L, `Cluster probability` = 0.5,
                   check.names = FALSE)
  out <- expect_committed(run(list(df)))$outputs[[1]]
  expect_equal(names(out), c("A", "Cluster", "Cluster probability"))
  expect_equal(out$Cluster, rep(1:2, each = 10))
})

test_that("empty inputs give empty outputs with the cluster fields", {
  df <- data.frame(Reading = character(0), Temperature = numeric(0))
  res <- expect_committed(run(list(df, df)))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(names(res$outputs[[1]]), c("Reading", "Temperature", "Cluster", "Cluster probability"))
  expect_equal(names(res$outputs[[2]]), c("Reading", "Temperature", "Cluster", "Cluster probability"))
  res <- expect_committed(run(list(readings, data.frame(Temperature = numeric(0), Vibration = numeric(0)))))
  expect_equal(nrow(res$outputs[[2]]), 0)
})

test_that("wrong types, missing fields, missing choices and no input abort with a message", {
  res <- run(list(data.frame(Name = c("a", "b"))))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "no Integer or Decimal fields")
  res <- run(list(data.frame(Name = c("a", "b"), A = 1:2)), useAllNumericFields = FALSE, fieldsToUse = "Name")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Only Integer and Decimal.*Name")
  res <- run(list(readings, data.frame(Temperature = 1)))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "not found in the second input: Vibration")
  res <- run(list(data.frame(A = 1:3)), useAllNumericFields = FALSE)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Choose the fields")
  res <- run(list(data.frame(A = c(2, 2, 2, 2))))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "No mixture model")
  res <- run(list())
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "No input data")
})

test_that("10,000 records on three fields fit in reasonable time", {
  set.seed(8)
  n <- 10000
  df <- data.frame(A = rnorm(n, rep(c(0, 5, 10), length.out = n)), B = rnorm(n), C = rnorm(n))
  elapsed <- system.time(out <- expect_committed(run(list(df)))$outputs[[1]])[["elapsed"]]
  expect_equal(nrow(out), n)
  expect_lt(elapsed, 120)
})
