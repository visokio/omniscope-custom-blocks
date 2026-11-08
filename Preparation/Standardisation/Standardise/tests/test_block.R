# Unit tests for the Standardise block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Preparation/Standardisation/Standardise
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

scores <- file.path(BLOCK_DIR, "sample-data", "supplier-scores.csv")
all_four <- c("Price", "Punctuality", "Defects", "LeadTime")

run <- function(input, ...) run_block(BLOCK_DIR, list(input), list(...))

test_that("the sample's four scores are rescaled to 0 to 1, other fields unchanged", {
  res <- expect_committed(run(scores, fields = all_four))
  out <- as.data.frame(res$outputs[[1]])
  input <- read.csv(scores, stringsAsFactors = FALSE)
  expect_equal(nrow(out), 12)
  expect_equal(names(out), names(input))
  expect_equal(out$Supplier, input$Supplier)
  expect_equal(out$Category, input$Category)
  for (f in all_four) {
    expect_equal(min(out[[f]], na.rm = TRUE), 0)
    expect_equal(max(out[[f]], na.rm = TRUE), 1)
  }
  # Price 95.4 to 112.3: Northwind's 104.5 is (104.5 - 95.4) / 16.9
  expect_equal(out$Price[out$Supplier == "Northwind Fasteners"], (104.5 - 95.4) / (112.3 - 95.4))
  expect_equal(out$LeadTime[out$Supplier == "Harbourside Labels"], 0)
  expect_equal(out$LeadTime[out$Supplier == "Brookside Electrical"], 1)
  expect_length(res$messages, 0)
})

test_that("a missing value stays missing and the rest of the field is still rescaled", {
  # The original took min() and max() with the missing value included, so the whole Punctuality field became empty
  out <- expect_committed(run(scores, fields = "Punctuality"))$outputs[[1]]
  expect_true(is.na(out$Punctuality[out$Supplier == "Marsh Lane Metals"]))
  expect_equal(sum(!is.na(out$Punctuality)), 11)
  expect_equal(out$Punctuality[out$Supplier == "Harbourside Labels"], 1)
  expect_equal(out$Punctuality[out$Supplier == "Brookside Electrical"], 0)
})

test_that("a field whose values are all the same becomes 0, with a message", {
  # The original divided by zero and gave NaN in every record
  res <- expect_committed(run(data.frame(a = c(3, 3, NA), b = c(1, 2, 3)), fields = c("a", "b")))
  out <- res$outputs[[1]]
  expect_equal(out$a, c(0, 0, NA))
  expect_equal(out$b, c(0, 0.5, 1))
  expect_match(res$messages, "All values the same, so set to 0: a")
})

test_that("whole-number fields come out as decimals", {
  out <- expect_committed(run(data.frame(n = c(10L, 20L, 15L)), fields = "n"))$outputs[[1]]
  expect_type(out$n, "double")
  expect_equal(out$n, c(0, 1, 0.5))
})

test_that("negative numbers and field names with spaces", {
  df <- data.frame(`Net margin` = c(-5, 0, 15), check.names = FALSE)
  out <- expect_committed(run(df, fields = "Net margin"))$outputs[[1]]
  expect_equal(out[["Net margin"]], c(0, 0.25, 1))
})

test_that("a field with only missing values stays missing", {
  out <- expect_committed(run(data.frame(a = c(NA_real_, NA_real_), b = 1:2), fields = "a"))$outputs[[1]]
  expect_true(all(is.na(out$a)))
})

test_that("empty input gives an empty output with the same fields", {
  res <- expect_committed(suppressWarnings(run(data.frame(a = numeric(0), s = character(0)), fields = "a")))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(names(res$outputs[[1]]), c("a", "s"))
})

test_that("text fields, no fields, a missing field or no input stop with a clear message", {
  # The original failed inside R for a text field and passed the data through unchanged with no fields chosen
  res <- run(scores, fields = c("Price", "Category"))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Only number fields.*Category")
  res <- run(scores)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Choose at least one field")
  res <- run(scores, fields = "Score")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Not in the input: Score")
  res <- run_block(BLOCK_DIR, list(), list(fields = "Price"))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Connect")
})

test_that("half a million records in a few seconds", {
  set.seed(1)
  n <- 500000
  df <- data.frame(id = seq_len(n), x = rnorm(n), y = runif(n, 10, 20))
  t <- system.time(res <- run(df, fields = c("x", "y")))
  out <- expect_committed(res)$outputs[[1]]
  expect_equal(range(out$x), c(0, 1))
  expect_equal(range(out$y), c(0, 1))
  expect_equal(out$id, df$id)
  expect_lt(t[["elapsed"]], 30)
})
