# Unit tests for the TSNE block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Analytics/Network-Analysis/TSNE
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

emails <- file.path(BLOCK_DIR, "sample-data", "email-network.csv")
teams <- read.csv(file.path(BLOCK_DIR, "tests", "teams.csv"), stringsAsFactors = FALSE)

run <- function(input, ...) run_block(BLOCK_DIR, list(input), list(...))

# Share of nodes whose nearest node on the map is in the same group
nearest.same <- function(out, group.of) {
  xy <- as.matrix(out[grep("^Dimension", names(out))])
  d <- as.matrix(dist(xy))
  diag(d) <- Inf
  g <- group.of(out$Node)
  mean(g == g[apply(d, 1, which.min)])
}
team.of <- function(name) teams$Team[match(name, teams$Name)]

test_that("sample: staff end up next to their own team", {
  out <- expect_committed(run(emails, from = "From", to = "To", weight = "Emails"))$outputs[[1]]
  expect_equal(names(out), c("Node", "Dimension 1", "Dimension 2", "Connections"))
  expect_equal(nrow(out), 60)
  expect_setequal(out$Node, teams$Name)
  expect_true(is.integer(out$Connections))
  expect_equal(nearest.same(out, team.of), 1)
})

test_that("the same input gives the same map on every run", {
  # t-SNE starts from random positions; the original set no seed, so the map changed on every run
  a <- expect_committed(run(emails, from = "From", to = "To", weight = "Emails"))$outputs[[1]]
  runif(10)
  b <- expect_committed(run(emails, from = "From", to = "To", weight = "Emails"))$outputs[[1]]
  expect_identical(a, b)
})

test_that("nodes that only receive connections are placed by who connects to them", {
  # people connect to topics; topics never connect onwards. The original gave every topic an empty
  # profile, so the topics could not be told apart
  set.seed(1)
  groups <- c("a", "b", "c")
  people <- data.frame(Person = sprintf("person%02d", 1:45), G = rep(groups, each = 15))
  topics <- data.frame(Topic = sprintf("topic%02d", 1:30), G = rep(groups, each = 10))
  rows <- do.call(rbind, lapply(seq_len(nrow(people)), function(i) {
    own <- topics$Topic[topics$G == people$G[i]]
    data.frame(From = people$Person[i], To = sample(own, 4))
  }))
  out <- expect_committed(run(rows, from = "From", to = "To", perplexity = 10))$outputs[[1]]
  group.of <- function(node) c(people$G, topics$G)[match(node, c(people$Person, topics$Topic))]
  topic.rows <- out[grepl("^topic", out$Node), ]
  expect_equal(nrow(topic.rows), 30)
  expect_gte(nearest.same(topic.rows, group.of), 0.9)
})

test_that("repeated connections add up instead of the last one counting", {
  d <- read.csv(emails, stringsAsFactors = FALSE)
  d <- d[!is.na(d$Emails), ]
  halves <- rbind(transform(d, Emails = Emails / 2), transform(d, Emails = Emails / 2))
  a <- expect_committed(run(d, from = "From", to = "To", weight = "Emails"))$outputs[[1]]
  b <- expect_committed(run(halves, from = "From", to = "To", weight = "Emails"))$outputs[[1]]
  expect_equal(a[, -4], b[, -4])
  expect_equal(b$Connections, a$Connections * 2L)
})

test_that("numeric node IDs, no weight, and 1 or 3 dimensions work", {
  # the original stopped with "\"From field\" must be of type text" for numeric IDs
  d <- read.csv(emails, stringsAsFactors = FALSE)
  ids <- setNames(seq_along(teams$Name), teams$Name)
  d$From <- unname(ids[d$From])
  d$To <- unname(ids[d$To])
  out <- expect_committed(run(d, from = "From", to = "To"))$outputs[[1]]
  expect_equal(nrow(out), 60)
  expect_true(is.character(out$Node))
  out1 <- expect_committed(run(d, from = "From", to = "To", outputDimensions = 1))$outputs[[1]]
  expect_equal(names(out1), c("Node", "Dimension 1", "Connections"))
  out3 <- expect_committed(run(d, from = "From", to = "To", outputDimensions = 3))$outputs[[1]]
  expect_equal(names(out3), c("Node", "Dimension 1", "Dimension 2", "Dimension 3", "Connections"))
})

test_that("an unset weight given as empty text means no weight", {
  out <- expect_committed(run(emails, from = "From", to = "To", weight = ""))$outputs[[1]]
  expect_equal(nrow(out), 60)
})

test_that("empty input gives an empty output with the fields", {
  df <- data.frame(From = character(0), To = character(0), Emails = numeric(0))
  out <- expect_committed(run(df, from = "From", to = "To", weight = "Emails"))$outputs[[1]]
  expect_equal(nrow(out), 0)
  expect_equal(names(out), c("Node", "Dimension 1", "Dimension 2", "Connections"))
})

test_that("bad options and inputs abort with a message", {
  small <- data.frame(From = c("a", "b", "c"), To = c("b", "c", "a"), W = c(1, 2, 3), T = "x")
  expect_match(run(small, from = "From", to = "To")$final_message, "too large for 3 nodes: use at most 0")
  expect_match(run(emails, from = "From", to = "To", outputDimensions = 4)$final_message, "must be 1, 2 or 3")
  expect_match(run(small, from = "From", to = "To", weight = "T")$final_message, "Weight field must be numeric")
  expect_match(run(transform(small, W = -W), from = "From", to = "To", weight = "W", perplexity = 0.5)$final_message,
               "negative")
  expect_match(run(small, to = "To")$final_message, "Choose the From field")
  expect_match(run(small, from = "From", to = "Nope")$final_message, "not found in the input: Nope")
  res <- run_block(BLOCK_DIR, list(), list(from = "From", to = "To"))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "No input data")
})

test_that("1,000 nodes take seconds", {
  set.seed(6)
  n <- 1000
  g <- rep(1:5, length.out = n)
  rows <- do.call(rbind, lapply(seq_len(n), function(i) {
    data.frame(From = i, To = sample(which(g == g[i]), 5), W = rpois(5, 5) + 1)
  }))
  elapsed <- system.time(out <- expect_committed(run(rows, from = "From", to = "To", weight = "W"))$outputs[[1]])[["elapsed"]]
  expect_equal(nrow(out), n)
  expect_lt(elapsed, 120)
})
