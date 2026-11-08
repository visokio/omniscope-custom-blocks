# Unit tests for the Attribute Analysis block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Analytics/Network-Analysis/Attribute-Analysis
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

assignments <- file.path(BLOCK_DIR, "sample-data", "project-assignments.csv")
fields <- c("From category", "To category", "Probability", "Connections")

run <- function(input, ...) run_block(BLOCK_DIR, list(input), list(...))
prob <- function(out, a, b) out$Probability[out$`From category` == a & out$`To category` == b]

test_that("sample: departments that share projects, with the same values as before", {
  out <- expect_committed(run(assignments, from = "Person", to = "Project", category = "Department"))$outputs[[1]]
  expect_equal(names(out), fields)
  expect_equal(nrow(out), 10)
  # values as the previous version of the script gave them
  expect_equal(prob(out, "Sales", "Marketing"), 0.68181818, tolerance = 1e-7)
  expect_equal(prob(out, "Marketing", "Sales"), 0.85714286, tolerance = 1e-7)
  expect_equal(prob(out, "Engineering", "Operations"), 0.73076923, tolerance = 1e-7)
  expect_equal(prob(out, "Finance", "Operations"), 0.66666667, tolerance = 1e-7)
  expect_equal(prob(out, "Engineering", "Marketing"), 0.07692308, tolerance = 1e-7)
  # sorted by From category, then strongest link first
  expect_equal(unique(out$`From category`), sort(unique(out$`From category`)))
  expect_equal(out$`To category`[out$`From category` == "Sales"], c("Marketing", "Finance"))
  expect_equal(out$Connections[out$`From category` == "Engineering"][1], 26L)
  # a category's probabilities add up to at most 1
  expect_true(all(tapply(out$Probability, out$`From category`, sum) <= 1 + 1e-9))
})

test_that("worked example: shares of connections to shared nodes, split between other categories", {
  df <- data.frame(Who = c("al", "bo", "cy", "di", "ed", "fi"), What = c("p1", "p1", "p1", "p2", "p2", "p3"),
                   Dept = c("S", "S", "E", "E", "O", "S"))
  out <- expect_committed(run(df, from = "Who", to = "What", category = "Dept"))$outputs[[1]]
  # S: 2 of its 3 connections go to p1, which E shares; its p3 connection is shared with nobody
  expect_equal(prob(out, "S", "E"), 2 / 3)
  # E: one connection to p1 (shared with S), one to p2 (shared with O)
  expect_equal(prob(out, "E", "S"), 1 / 2)
  expect_equal(prob(out, "E", "O"), 1 / 2)
  expect_equal(prob(out, "O", "E"), 1)
  expect_equal(nrow(out), 4)
  expect_equal(out$Connections[out$`From category` == "S"], 3L)
})

test_that("numeric node IDs work", {
  # the original stopped with "\"From field\" must be of type text"
  df <- data.frame(Who = 1:6, What = c(10L, 10L, 10L, 20L, 20L, 30L), Dept = c("S", "S", "E", "E", "O", "S"))
  out <- expect_committed(run(df, from = "Who", to = "What", category = "Dept"))$outputs[[1]]
  expect_equal(prob(out, "S", "E"), 2 / 3)
})

test_that("records with a missing value are left out", {
  out <- expect_committed(run(assignments, from = "Person", to = "Project", category = "Department"))$outputs[[1]]
  d <- read.csv(assignments, stringsAsFactors = FALSE, na.strings = "")
  expect_equal(sum(out$Connections[!duplicated(out$`From category`)]), sum(!is.na(d$Department)))
})

test_that("one category only, or nothing shared, gives an empty output with the fields", {
  df <- data.frame(Who = c("a", "b"), What = c("x", "x"), Dept = c("S", "S"))
  out <- expect_committed(run(df, from = "Who", to = "What", category = "Dept"))$outputs[[1]]
  expect_equal(nrow(out), 0)
  expect_equal(names(out), fields)
  df <- data.frame(Who = c("a", "b"), What = c("x", "y"), Dept = c("S", "T"))
  out <- expect_committed(run(df, from = "Who", to = "What", category = "Dept"))$outputs[[1]]
  expect_equal(nrow(out), 0)
})

test_that("empty input gives an empty output with the fields", {
  df <- data.frame(Who = character(0), What = character(0), Dept = character(0))
  out <- expect_committed(run(df, from = "Who", to = "What", category = "Dept"))$outputs[[1]]
  expect_equal(nrow(out), 0)
  expect_equal(names(out), fields)
})

test_that("missing choices and fields abort with a message", {
  df <- data.frame(Who = "a", What = "x", Dept = "S")
  expect_match(run(df, to = "What", category = "Dept")$final_message, "Choose the From field")
  expect_match(run(df, from = "Who", category = "Dept")$final_message, "Choose the To field")
  expect_match(run(df, from = "Who", to = "What")$final_message, "Choose the Category field")
  expect_match(run(df, from = "Who", to = "Nope", category = "Dept")$final_message, "not found in the input: Nope")
  res <- run_block(BLOCK_DIR, list(), list(from = "Who", to = "What", category = "Dept"))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "No input data")
})

test_that("200,000 connections in 20 categories take seconds", {
  set.seed(9)
  n <- 200000
  df <- data.frame(Who = sprintf("p%05d", sample(20000, n, replace = TRUE)),
                   What = sprintf("t%04d", sample(5000, n, replace = TRUE)),
                   Dept = sprintf("d%02d", sample(20, n, replace = TRUE)))
  elapsed <- system.time(out <- expect_committed(run(df, from = "Who", to = "What", category = "Dept"))$outputs[[1]])[["elapsed"]]
  expect_equal(nrow(out), 20 * 19)
  expect_lt(elapsed, 60)
})

test_that("the sample has the 85 assignments of 36 people that the showcase and make-sample.R describe", {
  d <- read.csv(assignments, stringsAsFactors = FALSE)
  expect_equal(nrow(d), 85)
  expect_equal(length(unique(d$Person)), 36)
})
