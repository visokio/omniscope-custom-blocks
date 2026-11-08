# Unit tests for the K-Nearest-Neighbours block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Analytics/Prediction/KNN
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

known <- file.path(BLOCK_DIR, "sample-data", "known-customers.csv")
new.customers <- file.path(BLOCK_DIR, "sample-data", "new-customers.csv")
truth <- read.csv(file.path(BLOCK_DIR, "tests", "true-segments.csv"), stringsAsFactors = FALSE)
true.segment <- function(customer) truth$Segment[match(customer, truth$Customer)]

run <- function(inputs, ...) run_block(BLOCK_DIR, inputs, list(...))

test_that("new customers get the segment of their nearest known customers", {
  out <- expect_committed(run(list(known, new.customers), fieldToPredict = "Segment"))$outputs[[1]]
  expect_equal(nrow(out), 15)
  expect_equal(names(out), c("Customer", "Annual Spend", "Orders Per Year", "Average Discount",
                             "Predicted (Segment)", "Vote share"))
  expect_equal(out$`Predicted (Segment)`, true.segment(out$Customer))
  expect_true(all(out$`Vote share` > 0.5 & out$`Vote share` <= 1))
})

test_that("one input: records without a segment are predicted, the others are predicted from the rest", {
  # the original failed with "no missing values are allowed" as soon as one record had no segment
  out <- expect_committed(run(list(known), fieldToPredict = "Segment"))$outputs[[1]]
  expect_equal(nrow(out), 126)
  expect_equal(names(out), c("Customer", "Annual Spend", "Orders Per Year", "Average Discount", "Segment",
                             "Predicted (Segment)", "Vote share"))
  unassigned <- is.na(out$Segment)
  expect_equal(sum(unassigned), 6)
  expect_equal(out$`Predicted (Segment)`[unassigned], true.segment(out$Customer[unassigned]))
  # 117 of the 120 known customers get their own segment back from their neighbours
  expect_equal(sum(out$`Predicted (Segment)`[!unassigned] == out$Segment[!unassigned]), 117)
})

test_that("a known record's own value is left out of its prediction", {
  # an isolated record whose neighbours all have another category: with itself counted it kept its own
  df <- data.frame(Class = c("a", "a", "a", "b"), X = c(1, 1.1, 1.2, 1.3))
  out <- expect_committed(run(list(df), fieldToPredict = "Class", numberOfNeighbours = 1))$outputs[[1]]
  expect_equal(out$`Predicted (Class)`[4], "a")
})

test_that("without standardising, spend outweighs the other fields", {
  a <- expect_committed(run(list(known), fieldToPredict = "Segment"))$outputs[[1]]
  b <- expect_committed(run(list(known), fieldToPredict = "Segment", standardise = FALSE))$outputs[[1]]
  right <- function(o) mean(o$`Predicted (Segment)` == true.segment(o$Customer))
  expect_equal(right(a), 123 / 126)
  expect_lt(right(b), 0.8)
})

test_that("the same input gives the same predictions, even with tied votes", {
  # four neighbours split two and two: R breaks the tie at random unless the seed is fixed
  df <- data.frame(Class = c("a", "a", "b", "b"), X = c(0, 2, 0.5, 1.5))
  new <- data.frame(X = rep(1, 30))
  a <- expect_committed(run(list(df, new), fieldToPredict = "Class", numberOfNeighbours = 3))$outputs[[1]]
  b <- expect_committed(run(list(df, new), fieldToPredict = "Class", numberOfNeighbours = 3))$outputs[[1]]
  expect_identical(a$`Predicted (Class)`, b$`Predicted (Class)`)
  expect_equal(unique(a$`Vote share`), 0.5)
})

test_that("records with a missing value keep their place, with an empty prediction", {
  new <- read.csv(new.customers, stringsAsFactors = FALSE, check.names = FALSE)
  new$`Orders Per Year`[3] <- NA
  out <- expect_committed(run(list(known, new), fieldToPredict = "Segment"))$outputs[[1]]
  expect_equal(out$Customer, new$Customer)
  expect_true(is.na(out$`Predicted (Segment)`[3]))
  expect_true(is.na(out$`Vote share`[3]))
  expect_equal(sum(is.na(out$`Predicted (Segment)`)), 1)
})

test_that("chosen fields are used, and fields to predict from may be Integer", {
  df <- data.frame(Class = c("lo", "lo", "lo", "hi", "hi", "hi"), A = c(1L, 2L, 3L, 10L, 11L, 12L), Noise = c(9, 1, 9, 1, 9, 1))
  new <- data.frame(A = c(2L, 11L), Noise = c(1, 9))
  out <- expect_committed(run(list(df, new), fieldToPredict = "Class", useAllNumericFields = FALSE,
                              fieldsToUse = "A", numberOfNeighbours = 3))$outputs[[1]]
  expect_equal(out$`Predicted (Class)`, c("lo", "hi"))
})

test_that("empty inputs give an empty output with the prediction fields", {
  empty.new <- data.frame(Customer = character(0), `Annual Spend` = numeric(0), `Orders Per Year` = integer(0),
                          `Average Discount` = numeric(0), check.names = FALSE)
  out <- expect_committed(run(list(known, empty.new), fieldToPredict = "Segment"))$outputs[[1]]
  expect_equal(nrow(out), 0)
  expect_equal(names(out), c(names(empty.new), "Predicted (Segment)", "Vote share"))
  empty.known <- data.frame(Segment = character(0), X = numeric(0))
  out <- expect_committed(run(list(empty.known), fieldToPredict = "Segment"))$outputs[[1]]
  expect_equal(names(out), c("Segment", "X", "Predicted (Segment)", "Vote share"))
})

test_that("bad choices and inputs abort with a message", {
  df <- data.frame(Class = c("a", "b", "a"), X = c(1, 2, 3), Code = c("x", "y", "z"))
  res <- run(list(df))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Choose the field to predict")
  res <- run(list(df), fieldToPredict = "X")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "must be a Text field")
  res <- run(list(df), fieldToPredict = "Class", useAllNumericFields = FALSE, fieldsToUse = "Code")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Only Integer and Decimal.*Code")
  res <- run(list(df, data.frame(Y = 1)), fieldToPredict = "Class")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "not found in the second input: X")
  res <- run(list(df, data.frame(X = 1)), fieldToPredict = "Class", numberOfNeighbours = 5)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "must be less than the number of records with a known Class \\(3\\)")
  res <- run(list(data.frame(Class = c(NA_character_, NA_character_), X = 1:2)), fieldToPredict = "Class")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "No records in the first input have a known Class")
  res <- run(list(), fieldToPredict = "Class")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "No input data")
})

test_that("20,000 known records and 20,000 to classify take seconds", {
  set.seed(7)
  n <- 20000
  make <- function() {
    cls <- sample(c("a", "b", "c"), n, replace = TRUE)
    data.frame(Class = cls, X = rnorm(n, match(cls, c("a", "b", "c")) * 3), Y = rnorm(n), stringsAsFactors = FALSE)
  }
  train <- make()
  test <- make()
  elapsed <- system.time(out <- expect_committed(run(list(train, test[, c("X", "Y")]), fieldToPredict = "Class"))$outputs[[1]])[["elapsed"]]
  expect_equal(nrow(out), n)
  expect_gt(mean(out$`Predicted (Class)` == test$Class), 0.8)
  expect_lt(elapsed, 60)
})
