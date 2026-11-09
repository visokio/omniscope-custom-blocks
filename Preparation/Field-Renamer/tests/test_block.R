# Unit tests for the Field Renamer block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Preparation/Field-Renamer
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

rules_csv <- file.path(BLOCK_DIR, "sample-data", "rename-rules.csv")
data_csv <- file.path(BLOCK_DIR, "sample-data", "crm-export.csv")

run <- function(rules, data, ...) {
  opts <- list(...)
  if (is.null(opts$currentNames)) opts$currentNames <- "Current Name"
  if (is.null(opts$newNames)) opts$newNames <- "New Name"
  run_block(BLOCK_DIR, list(rules, data), opts)
}
rules_df <- function(current, new) data.frame(`Current Name` = current, `New Name` = new, check.names = FALSE)

test_that("the sample rules rename five fields and report the unused rule and the unchanged fields", {
  res <- expect_committed(run(rules_csv, data_csv))
  out <- res$outputs[[1]]
  expect_equal(nrow(out), 12)
  expect_equal(names(out), c("Customer Number", "Customer Name", "town", "Postcode", "Account Manager",
                             "Last Order Date", "ytd_sales"))
  expect_equal(out[["Customer Name"]][1], "Fernhill Garden Centre")
  expect_equal(out$ytd_sales[3], 42915.75)
  expect_equal(res$outputs[[2]], data.frame(`Current Name` = "credit_lim", `New Name` = "Credit Limit",
                                            check.names = FALSE))
  expect_equal(res$outputs[[3]]$Field, c("town", "ytd_sales"))
})

test_that("values and types are unchanged", {
  data <- read.csv(data_csv, stringsAsFactors = FALSE)
  out <- expect_committed(run(rules_csv, data_csv))$outputs[[1]]
  expect_equal(unname(as.list(out))[c(1, 2, 3, 7)], unname(as.list(data))[c(1, 2, 3, 7)])
  expect_true(inherits(out[["Last Order Date"]], "POSIXct"))
  expect_true(is.na(out[["Last Order Date"]][11]))
})

test_that("names in the rules are trimmed, and matching is exact otherwise", {
  # The old introductory text's example had a space after "Isin"; it renamed nothing.
  data <- data.frame(Isin = "XS1", Category = "Sub", category = "x")
  res <- expect_committed(run(rules_df(c("Isin ", " Category"), c(" Isin Number", "New Category ")), data))
  expect_equal(names(res$outputs[[1]]), c("Isin Number", "New Category", "category"))
  expect_equal(nrow(res$outputs[[2]]), 0)
})

test_that("a rename onto an existing field name stops with a message", {
  # The original wrote two fields called "Name"
  data <- data.frame(Name = "a", Full = "b")
  res <- run(rules_df("Full", "Name"), data)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "same name: Name")
  # two rules giving the same new name
  res <- run(rules_df(c("Name", "Full"), c("X", "X")), data)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "same name: X")
})

test_that("swapping two names works", {
  data <- data.frame(A = 1L, B = "two")
  out <- expect_committed(run(rules_df(c("A", "B"), c("B", "A")), data))$outputs[[1]]
  expect_equal(names(out), c("B", "A"))
  expect_equal(out$B, 1L)
})

test_that("rules with no current name are skipped; a rule with no new name stops with a message", {
  data <- data.frame(A = 1L, B = 2L)
  out <- expect_committed(run(rules_df(c(NA, "A"), c("Z", "Alpha")), data))$outputs[[1]]
  expect_equal(names(out), c("Alpha", "B"))
  # The original failed with a data.table error ("NA in 'new'")
  res <- run(rules_df(c("A", "B"), c("Alpha", NA)), data)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "no new name: B")
})

test_that("duplicate current names stop with a message", {
  res <- run(rules_df(c("A", "A"), c("X", "Y")), data.frame(A = 1))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "duplicates: A")
})

test_that("empty inputs", {
  # no records in the data: the fields are still renamed
  data <- data.frame(cust_no = character(0), town = character(0))
  res <- expect_committed(run(rules_csv, data))
  expect_equal(names(res$outputs[[1]]), c("Customer Number", "town"))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(nrow(res$outputs[[2]]), 5)
  # no rules: the data passes through unchanged and every field is listed as unchanged
  res <- expect_committed(run(rules_df(character(0), character(0)), data_csv))
  expect_equal(names(res$outputs[[1]])[1], "cust_no")
  expect_equal(nrow(res$outputs[[3]]), 7)
  expect_equal(names(res$outputs[[2]]), c("Current Name", "New Name"))
})

test_that("rules held in number fields are compared as text", {
  data <- data.frame(`2024` = 1, `2025` = 2, check.names = FALSE)
  rules <- data.frame(Old = c(2024L, 2025L), New = c("Last year", "This year"))
  out <- expect_committed(run(rules, data, currentNames = "Old", newNames = "New"))$outputs[[1]]
  expect_equal(names(out), c("Last year", "This year"))
})

test_that("missing inputs and options stop with a message", {
  res <- run(rules_csv, NULL)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "second input")
  res <- run(NULL, data_csv)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "first input")
  res <- run_block(BLOCK_DIR, list(rules_csv, data_csv), list(newNames = "New Name"))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Current field names")
  res <- run(rules_csv, data_csv, newNames = "Nope")
  expect_equal(res$status, "aborted")
})

test_that("2,000 fields and 20,000 records", {
  n <- 2000
  data <- as.data.frame(matrix(1L, nrow = 20000, ncol = n))
  names(data) <- sprintf("f%04d", seq_len(n))
  rules <- rules_df(sprintf("f%04d", seq_len(n)), sprintf("Field %d", seq_len(n)))
  t0 <- Sys.time()
  res <- expect_committed(run(rules, data))
  expect_lt(as.numeric(Sys.time() - t0, units = "secs"), 30)
  expect_equal(names(res$outputs[[1]])[c(1, n)], c("Field 1", "Field 2000"))
})
