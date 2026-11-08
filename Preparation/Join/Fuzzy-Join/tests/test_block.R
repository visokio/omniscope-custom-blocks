# Unit tests for the Fuzzy Terms Join block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Preparation/Join/Fuzzy-Join
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

invoices <- file.path(BLOCK_DIR, "sample-data", "supplier-invoices.csv")
master <- file.path(BLOCK_DIR, "sample-data", "supplier-master.csv")

run <- function(input1, input2, ...) run_block(BLOCK_DIR, list(input1, input2), list(...))

expected_account <- c(
  "INV-1001" = "S-001", "INV-1002" = "S-001", "INV-1003" = "S-002", "INV-1004" = "S-002",
  "INV-1005" = "S-003", "INV-1006" = "S-003", "INV-1007" = "S-004", "INV-1008" = "S-004",
  "INV-1009" = "S-005", "INV-1010" = "S-005", "INV-1011" = "S-006", "INV-1012" = "S-006",
  "INV-1013" = "S-007", "INV-1014" = "S-007", "INV-1015" = "S-008", "INV-1016" = "S-008"
)

test_that("left join matches every invoice spelling to its supplier", {
  res <- expect_committed(run(invoices, master, left = "Supplier", right = "Name", joinType = "left"))
  out <- res$outputs[[1]]
  expect_equal(nrow(out), 16)
  expect_equal(names(out), c("Invoice", "Supplier", "Amount", "Account", "Name", "Category"))
  expect_equal(setNames(out$Account, out$Invoice)[names(expected_account)], expected_account)
})

test_that("left is the default join type", {
  res <- expect_committed(run(invoices, master, left = "Supplier", right = "Name"))
  expect_equal(nrow(res$outputs[[1]]), 16)
})

test_that("right join gives each second-input record its best match, however weak", {
  out <- expect_committed(run(invoices, master, left = "Supplier", right = "Name", joinType = "right"))$outputs[[1]]
  expect_equal(nrow(out), 10)
  expect_setequal(out$Account, sprintf("S-%03d", 1:10))
  # S-010 "Ashby Fleet Hire Ltd" shares only "ltd" with an invoice: there is no minimum score
  expect_true(out$Invoice[out$Account == "S-010"] %in% names(expected_account))
})

test_that("left + right stacks both joins; pairs found from both sides appear twice", {
  out <- expect_committed(run(invoices, master, left = "Supplier", right = "Name", joinType = "left+right"))$outputs[[1]]
  expect_equal(nrow(out), 26)
  expect_equal(sum(out$Invoice == "INV-1002" & out$Account == "S-001"), 2)
})

test_that("records with no word in common are left out", {
  left <- data.frame(Name = c("Alpha Mills", "Zebra"), V = 1:2)
  right <- data.frame(Org = c("Alpha Mills Ltd", "Gamma"), W = 3:4)
  out <- expect_committed(run(left, right, left = "Name", right = "Org"))$outputs[[1]]
  expect_equal(out$Name, "Alpha Mills")
})

test_that("case, punctuation, digits and one-letter words are ignored", {
  left <- data.frame(Name = c("Kay-Brothers (2019)", "B Mason & Sons"))
  right <- data.frame(Org = c("KAY BROTHERS", "mason, sons", "2019 B"))
  out <- expect_committed(run(left, right, left = "Name", right = "Org"))$outputs[[1]]
  expect_equal(out$Org, c("KAY BROTHERS", "mason, sons"))
})

test_that("punctuation inside a word splits it", {
  # "O'Neill" is the words "o" (ignored, one letter) and "neill"
  left <- data.frame(Name = "O'Neill")
  right <- data.frame(Org = c("Neill", "ONeill"))
  out <- expect_committed(run(left, right, left = "Name", right = "Org"))$outputs[[1]]
  expect_equal(out$Org, "Neill")
})

test_that("words that are rare in the matched-from input outweigh common ones", {
  # in a Left join the weights come from the first input, where "ltd" is common and "kestrel" rare
  left <- data.frame(Name = c("Kestrel Supplies Ltd", "Alpha Ltd", "Beta Ltd", "Gamma Ltd"))
  right <- data.frame(Org = c("Kestrel Group", "Northern Ltd"))
  out <- expect_committed(run(left, right, left = "Name", right = "Org"))$outputs[[1]]
  expect_equal(out$Org[out$Name == "Kestrel Supplies Ltd"], "Kestrel Group")
})

test_that("more shared words score higher, and a tie goes to the later record", {
  left <- data.frame(Name = "Kestrel Supplies Ltd")
  right <- data.frame(Org = c("Supplies Ltd", "Kestrel Group", "More Supplies Ltd"))
  out <- expect_committed(run(left, right, left = "Name", right = "Org"))$outputs[[1]]
  expect_equal(out$Org, "More Supplies Ltd")
})

test_that("left + right with the same field name on both sides keeps .x for the first input", {
  left <- data.frame(Name = c("Acme Widgets Ltd", "Blue Harbour Foods"), V = 1:2)
  right <- data.frame(Name = c("ACME Widgets Limited", "Harbour Foods (Blue)", "Zed"), W = 3:5)
  out <- expect_committed(run(left, right, left = "Name", right = "Name", joinType = "left+right"))$outputs[[1]]
  expect_equal(nrow(out), 4)
  expect_true(all(out$Name.x %in% left$Name))
  expect_true(all(out$Name.y %in% right$Name))
})

test_that("a right join on its own keeps its original suffixes (.x for the second input)", {
  left <- data.frame(Name = c("Acme Widgets Ltd"), V = 1L)
  right <- data.frame(Name = c("ACME Widgets Limited"), W = 3L)
  out <- expect_committed(run(left, right, left = "Name", right = "Name", joinType = "right"))$outputs[[1]]
  expect_equal(out$Name.x, "ACME Widgets Limited")
  expect_equal(out$Name.y, "Acme Widgets Ltd")
})

test_that("field names with spaces come out with dots (current behaviour)", {
  left <- data.frame(`Supplier Name` = "Acme Widgets", check.names = FALSE)
  right <- data.frame(`Registered Name` = "Acme Widgets Ltd", check.names = FALSE)
  out <- expect_committed(run(left, right, left = "Supplier Name", right = "Registered Name"))$outputs[[1]]
  expect_equal(names(out), c("Supplier.Name", "Registered.Name"))
})

test_that("missing text does not match missing text", {
  left <- data.frame(a = c(NA, "x y"))
  right <- data.frame(b = c(NA, "zz"))
  out <- expect_committed(suppressWarnings(run(left, right, left = "a", right = "b")))$outputs[[1]]
  expect_equal(nrow(out), 0)
  expect_equal(names(out), c("a", "b"))
})

test_that("empty inputs give an empty output with the joined fields", {
  left <- data.frame(Name = c("Acme Widgets Ltd"), V = 1L)
  right <- data.frame(Org = character(0), W = integer(0))
  for (jt in c("left", "right", "left+right")) {
    res <- suppressWarnings(run(left, right, left = "Name", right = "Org", joinType = jt))
    expect_committed(res)
    expect_equal(nrow(res$outputs[[1]]), 0)
    expect_setequal(names(res$outputs[[1]]), c("Name", "V", "Org", "W"))
    res <- suppressWarnings(run(right, left, left = "Org", right = "Name", joinType = jt))
    expect_committed(res)
    expect_equal(nrow(res$outputs[[1]]), 0)
  }
})

test_that("a field that is not text, or a missing input, stops with a clear message", {
  left <- data.frame(Name = "Acme", Num = 1.5)
  right <- data.frame(Org = "Acme Ltd")
  res <- run(left, right, left = "Num", right = "Org")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Left field")
  res <- run_block(BLOCK_DIR, list(left), list(left = "Name", right = "Org"))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "right")
  res <- run(left, data.frame(Org = "Acme", .index = 1L), left = "Name", right = "Org")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "second input")
})

test_that("ten thousand records a side join in seconds when no word is in most records", {
  set.seed(1)
  vocab <- vapply(1:3000, function(i) paste(sample(letters, 7, TRUE), collapse = ""), "")
  names3 <- function(n) vapply(seq_len(n), function(i) paste(sample(vocab, 3), collapse = " "), "")
  left <- data.frame(Name = names3(10000), id = 1:10000)
  right <- data.frame(Org = names3(10000), rid = 1:10000)
  t <- system.time(res <- run(left, right, left = "Name", right = "Org", joinType = "left+right"))
  expect_committed(res)
  expect_equal(nrow(res$outputs[[1]]), 20000)
  expect_lt(t[["elapsed"]], 60)
})
