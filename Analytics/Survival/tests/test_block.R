# Unit tests for the Survival Analysis block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Analytics/Survival
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

subs <- file.path(BLOCK_DIR, "sample-data", "subscriptions.csv")

run <- function(input, ...) run_block(BLOCK_DIR, list(input), list(...))
curve.fields <- c("Time", "At risk", "Events", "Censored", "Survival", "Lower 95%", "Upper 95%",
                  "Std error (log survival)")
summary.fields <- c("Records", "Events", "Censored", "Median time", "Median lower 95%", "Median upper 95%")

test_that("sample: one curve per plan, starting at time 0, and a summary per plan", {
  res <- expect_committed(run(subs, time = "Months", event = "Cancelled", strata = "Plan"))
  curve <- res$outputs[[1]]
  expect_equal(names(curve), c("Plan", curve.fields))
  expect_equal(unique(curve$Plan), c("Annual", "Monthly"))
  expect_equal(curve$Time[curve$Plan == "Annual"][1:3], c(0, 3, 4))
  expect_equal(curve$Survival[curve$Time == 0], c(1, 1))
  expect_equal(curve$`At risk`[curve$Time == 0], c(79L, 100L))  # one Annual record has no Months
  expect_true(all(diff(curve$Survival[curve$Plan == "Monthly"]) <= 0))
  # Annual subscribers mostly leave at the 12-month renewal
  annual <- curve[curve$Plan == "Annual", ]
  expect_equal(annual$Events[annual$Time == 12], 16L)
  expect_equal(nrow(curve), 42 + 2)

  s <- res$outputs[[2]]
  expect_equal(names(s), c("Plan", summary.fields))
  expect_equal(s$Plan, c("Annual", "Monthly"))
  expect_equal(s$Records, c(79L, 100L))
  expect_equal(s$Events, c(20L, 70L))
  expect_equal(s$Censored, c(59L, 30L))
  expect_equal(s$`Median time`, c(24, 8))
  expect_true(is.na(s$`Median upper 95%`[1]))  # too few Annual subscribers left at 24 months for an upper limit
})

test_that("values match the previous version of the block on the sample", {
  # survival and confidence limits as the ggfortify-based script gave them, overall curve
  curve <- expect_committed(run(subs, time = "Months", event = "Cancelled"))$outputs[[1]]
  expect_equal(names(curve), curve.fields)
  at <- function(t, f) curve[[f]][curve$Time == t]
  expect_equal(at(1, "Survival"), 0.9608939, tolerance = 1e-6)
  expect_equal(at(4, "Survival"), 0.8016564, tolerance = 1e-6)
  expect_equal(at(4, "Lower 95%"), 0.7448391, tolerance = 1e-6)
  expect_equal(at(4, "Upper 95%"), 0.8628078, tolerance = 1e-6)
  expect_equal(at(3, "At risk"), 162L)
  expect_equal(at(3, "Censored"), 9L)
  fh <- expect_committed(run(subs, time = "Months", event = "Cancelled", type = "fleming-harrington"))$outputs[[1]]
  expect_equal(fh$Survival[fh$Time == 1], 0.9616486, tolerance = 1e-6)
  expect_equal(fh$Survival[fh$Time == 4], 0.8066075, tolerance = 1e-6)
})

test_that("Kaplan-Meier and Fleming-Harrington follow their formulas", {
  # times 1..6; censored at 2 and 5
  df <- data.frame(T = 1:6, E = c(1, 0, 1, 1, 0, 1))
  km <- expect_committed(run(df, time = "T", event = "E"))$outputs[[1]]
  expect_equal(km$Time, 0:6)
  expect_equal(km$`At risk`, c(6L, 6L, 5L, 4L, 3L, 2L, 1L))
  expect_equal(km$Survival, cumprod(c(1, 5 / 6, 1, 3 / 4, 2 / 3, 1, 0)))
  expect_true(is.na(km$`Lower 95%`[7]))  # no interval once survival reaches 0
  fh <- expect_committed(run(df, time = "T", event = "E", type = "fleming-harrington"))$outputs[[1]]
  expect_equal(fh$Survival, exp(-cumsum(c(0, 1 / 6, 0, 1 / 4, 1 / 3, 0, 1))))
})

test_that("events coded 1 / 2 or true / false give the same curve as 0 / 1", {
  df <- data.frame(T = c(2, 3, 3, 5, 8), E = c(1L, 0L, 1L, 1L, 0L))
  ref <- expect_committed(run(df, time = "T", event = "E"))$outputs[[1]]
  df2 <- transform(df, E = E + 1L)
  expect_equal(expect_committed(run(df2, time = "T", event = "E"))$outputs[[1]], ref)
  df3 <- transform(df, E = E == 1)
  expect_equal(expect_committed(run(df3, time = "T", event = "E"))$outputs[[1]], ref)
})

test_that("an unset Group given as empty text gives one curve", {
  df <- data.frame(T = c(2, 3, 4), E = c(1, 1, 0))
  out <- expect_committed(run(df, time = "T", event = "E", strata = ""))$outputs[[1]]
  expect_equal(names(out), curve.fields)
})

test_that("missing values are left out; a group with one value still has its name", {
  df <- data.frame(T = c(2, NA, 4, 5), E = c(1, 1, NA, 0), G = c("x", "x", "x", NA))
  res <- expect_committed(run(df, time = "T", event = "E", strata = "G"))
  expect_equal(res$outputs[[2]]$G, "x")
  expect_equal(res$outputs[[2]]$Records, 1L)
  expect_equal(res$outputs[[1]]$G, c("x", "x"))
})

test_that("empty input gives empty outputs with the fields", {
  df <- data.frame(T = numeric(0), E = integer(0), G = character(0))
  res <- expect_committed(run(df, time = "T", event = "E", strata = "G"))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(names(res$outputs[[1]]), c("G", curve.fields))
  expect_equal(names(res$outputs[[2]]), c("G", summary.fields))
})

test_that("wrong types and missing choices abort with a message", {
  df <- data.frame(T = c(1, 2), E = c("yes", "no"), D = as.POSIXct(c("2026-01-01", "2026-02-01"), tz = "UTC"),
                   N = c(-1, 2), C = c(0, 3))
  expect_match(run(df, time = "T", event = "E")$final_message, "Event field must be")
  expect_match(run(df, time = "T", event = "C")$final_message, "found 0, 3")
  expect_match(run(df, time = "D", event = "C")$final_message, "Time field must be a number")
  expect_match(run(df, time = "N", event = "C")$final_message, "negative")
  expect_match(run(df, event = "C")$final_message, "Choose the Time field")
  expect_match(run(df, time = "T", event = "C", strata = "Nope")$final_message, "not found in the input: Nope")
  res <- run_block(BLOCK_DIR, list(), list(time = "T", event = "E"))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "No input data")
})

test_that("100,000 subjects in 50 groups take seconds", {
  set.seed(4)
  n <- 100000
  df <- data.frame(T = rexp(n, 0.1), E = rbinom(n, 1, 0.7), G = sprintf("g%02d", sample(50, n, replace = TRUE)))
  elapsed <- system.time(res <- expect_committed(run(df, time = "T", event = "E", strata = "G")))[["elapsed"]]
  expect_equal(nrow(res$outputs[[2]]), 50)
  expect_equal(sum(res$outputs[[2]]$Records), n)
  expect_lt(elapsed, 60)
})
