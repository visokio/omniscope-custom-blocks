# Unit tests for the Inequality Join block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Preparation/Join/Inequality-Join
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

orders <- file.path(BLOCK_DIR, "sample-data", "orders.csv")
campaigns <- file.path(BLOCK_DIR, "sample-data", "campaigns.csv")

run <- function(input1, input2, ...) run_block(BLOCK_DIR, list(input1, input2), list(...))
sample_options <- list(left = "Ordered", comparator = ">=", right = "Sent", leftKey = "Customer", rightKey = "Customer")
run_sample <- function(...) do.call(run, c(list(orders, campaigns), sample_options, list(...)))

test_that("each order gets every campaign sent to its customer on or before the order date", {
  res <- expect_committed(run_sample())
  out <- res$outputs[[1]]
  expect_equal(names(out), c("Order", "Customer", "Ordered", "Amount", "Campaign", "Customer.1", "Sent"))
  expect_equal(nrow(out), 7)
  expect_equal(paste(out$Order, out$Campaign), c(
    "SO-501 Winter offer", "SO-502 Winter offer", "SO-502 Spring launch", "SO-503 Winter offer",
    "SO-505 Winter offer", "SO-505 Loyalty voucher", "SO-506 Spring launch"))
  expect_true(all(out$Customer == out$Customer.1))
  expect_true(all(out$Ordered >= out$Sent))
  expect_equal(res$final_message, "5 of 8 first-input records matched; 7 records out")
})

test_that("a left join keeps the orders with no earlier campaign, in input order", {
  out <- expect_committed(run_sample(joinType = "left"))$outputs[[1]]
  expect_equal(nrow(out), 10)
  expect_equal(unique(out$Order), sprintf("SO-%d", 501:508))
  expect_equal(out$Order[is.na(out$Campaign)], c("SO-504", "SO-507", "SO-508"))
  expect_s3_class(out$Sent, "POSIXct")
})

test_that("without an equal field every pair that satisfies the comparison is joined", {
  out <- expect_committed(run(orders, campaigns, left = "Ordered", comparator = ">=", right = "Sent"))$outputs[[1]]
  # 8 orders x 8 campaigns, kept where Ordered >= Sent
  o <- read.csv(orders); c <- read.csv(campaigns)
  expected <- sum(outer(as.Date(o$Ordered), as.Date(c$Sent), ">="))
  expect_equal(nrow(out), expected)
})

test_that("every comparator", {
  left <- data.frame(id = 1:3, v = c(1, 5, 9))
  right <- data.frame(t = c(5))
  ids <- function(cmp) expect_committed(run(left, right, left = "v", right = "t", comparator = cmp))$outputs[[1]]$id
  expect_equal(ids("=="), 2L)
  expect_equal(ids("<="), 1:2)
  expect_equal(ids("<"), 1L)
  expect_equal(ids(">="), 2:3)
  expect_equal(ids(">"), 3L)
})

test_that(">= is the default comparator and inner the default join type", {
  out <- expect_committed(run(data.frame(v = c(1, 9)), data.frame(t = 5), left = "v", right = "t"))$outputs[[1]]
  expect_equal(out$v, 9)
})

test_that("output follows the first input's order, then the second's", {
  left <- data.frame(id = c("a", "b"), v = c(10, 3))
  right <- data.frame(name = c("p", "q", "r"), t = c(2, 1, 5))
  out <- expect_committed(run(left, right, left = "v", right = "t", comparator = ">"))$outputs[[1]]
  expect_equal(paste0(out$id, out$name), c("ap", "aq", "ar", "bp", "bq"))
})

test_that("a field name in both inputs gets .1 on the second input's copy", {
  out <- expect_committed(run(data.frame(v = c(1, 5)), data.frame(v = 4), left = "v", right = "v",
                              comparator = "<="))$outputs[[1]]
  expect_equal(names(out), c("v", "v.1"))
  expect_equal(out$v, 1)
  expect_equal(out$v.1, 4)
})

test_that("field names with spaces are kept", {
  left <- data.frame(`Order value` = c(1, 5), check.names = FALSE)
  right <- data.frame(`Credit limit` = 4, check.names = FALSE)
  out <- expect_committed(run(left, right, left = "Order value", right = "Credit limit", comparator = "<="))$outputs[[1]]
  expect_equal(names(out), c("Order value", "Credit limit"))
})

test_that("missing values match nothing, and are kept by a left join", {
  left <- data.frame(id = 1:3, v = c(1, NA, 3), k = c("a", "a", NA))
  right <- data.frame(t = c(5, NA), k = c("a", "a"))
  inner <- expect_committed(run(left, right, left = "v", right = "t", comparator = "<", leftKey = "k",
                                rightKey = "k"))$outputs[[1]]
  expect_equal(inner$id, 1L)
  outer <- expect_committed(run(left, right, left = "v", right = "t", comparator = "<", leftKey = "k",
                                rightKey = "k", joinType = "left"))$outputs[[1]]
  expect_equal(outer$id, 1:3)
  expect_equal(outer$t, c(5, NA, NA))
})

test_that("numbers against dates, text fields and mismatched equal fields abort with a message", {
  res <- run(data.frame(d = c("2026-01-01", "2026-02-01")), data.frame(t = 5), left = "d", right = "t")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "both be numbers or both be dates")
  res <- run(data.frame(v = c("a", "b")), data.frame(t = 5), left = "v", right = "t")
  expect_match(res$final_message, "must be a number or date field")
  res <- run(data.frame(v = 1, k = "a"), data.frame(t = 5, k = 1L), left = "v", right = "t", leftKey = "k",
             rightKey = "k")
  expect_match(res$final_message, "same type")
})

test_that("missing choices, unknown fields, one equal field and missing inputs abort with a message", {
  res <- run(data.frame(v = 1), data.frame(t = 5), right = "t")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Left field")
  res <- run(data.frame(v = 1), data.frame(t = 5), left = "v", right = "x")
  expect_match(res$final_message, "no field called \"x\"")
  res <- run(data.frame(v = 1, k = "a"), data.frame(t = 5), left = "v", right = "t", leftKey = "k")
  expect_match(res$final_message, "both inputs")
  res <- run_block(BLOCK_DIR, list(data.frame(v = 1)), list(left = "v", right = "t"))
  expect_match(res$final_message, "second")
})

test_that("empty inputs give an empty output with the joined fields", {
  left <- data.frame(v = numeric(0), n = character(0))
  right <- data.frame(t = 5, w = "x")
  for (jt in c("inner", "left")) {
    out <- expect_committed(run(left, right, left = "v", right = "t", joinType = jt))$outputs[[1]]
    expect_equal(nrow(out), 0)
    expect_equal(names(out), c("v", "n", "t", "w"))
  }
  out <- expect_committed(run(data.frame(v = 1:2), right[0, ], left = "v", right = "t", joinType = "left"))$outputs[[1]]
  expect_equal(nrow(out), 2)
  expect_true(all(is.na(out$w)))
})

test_that("10,000 records a side with an equal field", {
  set.seed(1)
  n <- 10000
  left <- data.frame(k = sample(1:500, n, TRUE), v = runif(n, 0, 100))
  right <- data.frame(k = sample(1:500, n, TRUE), t = runif(n, 0, 100))
  t0 <- Sys.time()
  out <- expect_committed(run(left, right, left = "v", right = "t", comparator = "<", leftKey = "k",
                              rightKey = "k"))$outputs[[1]]
  expect_lt(as.numeric(difftime(Sys.time(), t0, units = "secs")), 30)
  expect_true(all(out$v < out$t & out$k == out$k.1))
  # same count as a brute-force check per key
  expected <- sum(vapply(split(seq_len(n), left$k), function(ix) {
    tt <- right$t[right$k == left$k[ix[1]]]
    sum(outer(left$v[ix], tt, "<"))
  }, numeric(1)))
  expect_equal(nrow(out), expected)
})
