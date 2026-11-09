# Unit tests for the KMeans block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Analytics/Clustering/KMeans
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

stores <- file.path(BLOCK_DIR, "sample-data", "store-metrics.csv")
formats <- read.csv(file.path(BLOCK_DIR, "tests", "store-formats.csv"), stringsAsFactors = FALSE)

run <- function(input, ...) run_block(BLOCK_DIR, list(input), list(...))

# How well clusters match known groups: the share of records in their cluster's most common group
purity <- function(cluster, group) {
  ok <- !is.na(cluster)
  sum(tapply(group[ok], cluster[ok], function(g) max(table(g)))) / sum(ok)
}

test_that("the sample's four shop formats come out as the four clusters", {
  out <- expect_committed(run(stores))$outputs[[1]]
  expect_equal(nrow(out), 80)
  expect_equal(names(out), c("Store", "Region", "Weekly Sales", "Footfall", "Cluster"))
  expect_true(is.integer(out$Cluster))
  expect_equal(purity(out$Cluster, formats$Format[match(out$Store, formats$Store)]), 1)
  expect_equal(as.vector(table(out$Cluster)), c(24, 20, 22, 13))
  expect_equal(unique(out$Cluster[!is.na(out$Cluster)]), 1:4)  # numbered in order of first appearance
})

test_that("without standardising, sales outweigh footfall and the formats mix", {
  out <- expect_committed(run(stores, standardise = FALSE))$outputs[[1]]
  expect_lt(purity(out$Cluster, formats$Format[match(out$Store, formats$Store)]), 0.9)
})

test_that("a record with a missing value keeps its place, with an empty cluster", {
  # the original dropped such records, so the output had fewer records than the input
  out <- expect_committed(run(stores))$outputs[[1]]
  expect_equal(out$Store, sprintf("ST-%03d", 1:80))
  expect_true(is.na(out$Cluster[out$Store == "ST-017"]))
  expect_equal(sum(is.na(out$Cluster)), 1)
})

test_that("the same input gives the same clusters on every run", {
  # the original used a random start, so clusters and their numbers could change between runs
  a <- expect_committed(run(stores))$outputs[[1]]$Cluster
  set.seed(99); runif(5)
  b <- expect_committed(run(stores))$outputs[[1]]$Cluster
  expect_identical(a, b)
})

test_that("chosen fields and the number of clusters are used", {
  df <- data.frame(Name = letters[1:9], A = c(1, 2, 3, 11, 12, 13, 21, 22, 23), B = c(5, 1, 9, 2, 8, 3, 7, 4, 6))
  out <- expect_committed(run(df, useAllNumericFields = FALSE, fieldsToUse = "A", numClusters = 3))$outputs[[1]]
  expect_equal(out$Cluster, rep(1:3, each = 3))
  out <- expect_committed(run(df, numClusters = 1))$outputs[[1]]
  expect_equal(out$Cluster, rep(1L, 9))
})

test_that("an existing Cluster field is replaced, not duplicated or clustered on", {
  df <- data.frame(A = c(1, 2, 10, 11), Cluster = c(9L, 9L, 9L, 9L))
  out <- expect_committed(run(df, numClusters = 2))$outputs[[1]]
  expect_equal(names(out), c("A", "Cluster"))
  expect_equal(out$Cluster, c(1L, 1L, 2L, 2L))
})

test_that("Integer fields and a constant field work", {
  df <- data.frame(A = c(1L, 2L, 10L, 11L), Same = 5L)
  out <- expect_committed(run(df, numClusters = 2))$outputs[[1]]
  expect_equal(out$Cluster, c(1L, 1L, 2L, 2L))
})

test_that("empty input gives an empty output with a Cluster field", {
  df <- data.frame(Store = character(0), Sales = numeric(0))
  out <- expect_committed(run(df))$outputs[[1]]
  expect_equal(nrow(out), 0)
  expect_equal(names(out), c("Store", "Sales", "Cluster"))
})

test_that("too many clusters for the data aborts with a message", {
  df <- data.frame(A = c(1, 1, 2, 2))
  res <- run(df, numClusters = 3)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "only 2 distinct")
})

test_that("wrong types, missing choices and no input abort with a message", {
  df <- data.frame(Name = c("a", "b"), When = as.POSIXct(c("2026-01-01", "2026-02-01"), tz = "UTC"))
  res <- run(df)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "no Integer or Decimal fields")
  res <- run(data.frame(Name = c("a", "b"), A = 1:2), useAllNumericFields = FALSE, fieldsToUse = "Name")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Only Integer and Decimal fields.*Name")
  res <- run(data.frame(A = 1:2), useAllNumericFields = FALSE)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Choose the fields")
  res <- run_block(BLOCK_DIR, list(), list())
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "No input data")
})

test_that("50,000 records cluster in a few seconds", {
  set.seed(3)
  n <- 50000
  df <- data.frame(A = rnorm(n, rep(c(0, 10, 20, 30, 40), length.out = n)), B = rnorm(n), C = runif(n))
  elapsed <- system.time(out <- expect_committed(run(df, numClusters = 5))$outputs[[1]])[["elapsed"]]
  expect_equal(nrow(out), n)
  expect_equal(length(unique(out$Cluster)), 5)
  expect_lt(elapsed, 30)
})
