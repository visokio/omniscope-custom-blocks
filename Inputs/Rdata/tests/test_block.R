# Unit tests for the R Data Reader block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Inputs/Rdata
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

rdata <- file.path(BLOCK_DIR, "sample-data", "store-survey.RData")
rds <- file.path(BLOCK_DIR, "sample-data", "stores.rds")

run <- function(...) run_block(BLOCK_DIR, list(), list(...))

save_tmp <- function(..., ext = "RData") {
  path <- tempfile(fileext = paste0(".", ext))
  objs <- list(...)
  env <- list2env(objs)
  if (ext == "rds") saveRDS(objs[[1]], path) else save(list = names(objs), envir = env, file = path)
  path
}

test_that("the sample .RData file loads the first table saved, not the note before it", {
  res <- expect_committed(run(rda_file = rdata))
  out <- res$outputs[[1]]
  expect_equal(nrow(out), 24)
  expect_equal(names(out), c("Response", "Store", "Visited", "Score", "Spend", "Recommend"))
  expect_type(out$Store, "character")            # factor -> text
  expect_s3_class(out$Visited, "POSIXct")        # Date -> date-time at midnight UTC
  expect_equal(format(out$Visited[1], tz = "UTC"), "2025-04-07")
  expect_equal(sum(is.na(out$Score)), 1)
  expect_equal(sum(out$Recommend, na.rm = TRUE), 16)
  expect_match(res$final_message, "Loaded 'responses': 24 records, 6 fields")
})

test_that("the objects output lists every object in the order saved, with what was loaded", {
  objs <- expect_committed(run(rda_file = rdata))$outputs[[2]]
  expect_equal(objs$Object, c("survey_note", "responses", "stores"))
  expect_equal(objs$Class, c("character", "data.frame", "data.frame"))
  expect_equal(objs$Records, c(1L, 24L, 4L))
  expect_equal(objs$Fields, c(1L, 6L, 4L))
  expect_equal(objs$Loaded, c(FALSE, TRUE, FALSE))
})

test_that("a named object loads, and meaningful row names become a field", {
  out <- expect_committed(run(rda_file = rdata, obj = "stores"))$outputs[[1]]
  expect_equal(names(out), c("Row name", "Town", "Opened", "Floorspace"))
  expect_equal(out$`Row name`, c("BRI", "LDS", "NWC", "OXF"))
})

test_that("a .rds file loads its object and lists it", {
  res <- expect_committed(run(rda_file = rds))
  expect_equal(nrow(res$outputs[[1]]), 4)
  expect_equal(res$outputs[[1]]$Town[3], "Newcastle")
  expect_equal(res$outputs[[2]]$Object, "stores")
  expect_true(res$outputs[[2]]$Loaded)
})

test_that("an object name with spaces around it, or an empty one, is handled", {
  out <- expect_committed(run(rda_file = rdata, obj = "  stores "))$outputs[[1]]
  expect_equal(nrow(out), 4)
  out <- expect_committed(run(rda_file = rdata, obj = ""))$outputs[[1]]
  expect_equal(nrow(out), 24)
})

test_that("a vector, a named vector, a matrix and a list of columns convert to tables", {
  path <- save_tmp(v = c(3, 1, 2), nv = c(a = 1L, b = 2L), m = matrix(1:6, 2), l = list(x = 1:2, y = c("p", "q")))
  expect_equal(expect_committed(run(rda_file = path, obj = "v"))$outputs[[1]], data.frame(Value = c(3, 1, 2)))
  expect_equal(expect_committed(run(rda_file = path, obj = "nv"))$outputs[[1]],
               data.frame(Name = c("a", "b"), Value = 1:2))
  expect_equal(names(expect_committed(run(rda_file = path, obj = "m"))$outputs[[1]]), c("V1", "V2", "V3"))
  expect_equal(expect_committed(run(rda_file = path, obj = "l"))$outputs[[1]]$y, c("p", "q"))
})

test_that("list fields become text and repeated field names are made unique", {
  df <- data.frame(id = 1:2)
  df$tags <- list(c("a", "b"), "c")
  df2 <- data.frame(a = 1, a = 2, check.names = FALSE)
  path <- save_tmp(df = df, df2 = df2)
  out <- expect_committed(run(rda_file = path, obj = "df"))$outputs[[1]]
  expect_equal(out$tags, c("a, b", "c"))
  expect_equal(names(expect_committed(run(rda_file = path, obj = "df2"))$outputs[[1]]), c("a", "a 1"))
})

test_that("an empty data frame gives an empty output with its fields", {
  path <- save_tmp(empty = data.frame(a = integer(0), b = character(0)))
  res <- expect_committed(run(rda_file = path))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(names(res$outputs[[1]]), c("a", "b"))
})

test_that("an object that is not a table stops with a message naming its class", {
  fit <- lm(mpg ~ wt, data = mtcars)
  path <- save_tmp(fit = fit, f = function(x) x)
  res <- run(rda_file = path, obj = "fit")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "'fit' is a lm")
  res <- run(rda_file = path)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "No object in the file can be read as a table")
})

test_that("a missing object name lists the objects in the file", {
  res <- run(rda_file = rdata, obj = "sales")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "no object called 'sales'.*survey_note, responses, stores")
})

test_that("missing, unsupported and unreadable files stop with a clear message", {
  res <- run(rda_file = file.path(tempdir(), "nope.rds"))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "File not found")
  csv <- tempfile(fileext = ".csv"); writeLines("a,b", csv)
  res <- run(rda_file = csv)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Unsupported file type '.csv'")
  bad <- tempfile(fileext = ".rds"); writeLines("not an R file", bad)
  res <- run(rda_file = bad)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Could not read .* as an R data file")
  res <- run_block(BLOCK_DIR, list(), list())
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Choose an R data file")
})

test_that("a .rds file with an object name set says a .rds file has one object", {
  res <- run(rda_file = rds, obj = "other")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "single object")
})

test_that("a data frame of 200,000 records loads in seconds", {
  big <- data.frame(id = seq_len(200000), g = factor(sample(letters, 200000, TRUE)), v = runif(200000))
  path <- save_tmp(big = big, ext = "rds")
  t <- system.time(res <- run(rda_file = path))
  expect_committed(res)
  expect_equal(nrow(res$outputs[[1]]), 200000)
  expect_type(res$outputs[[1]]$g, "character")
  expect_lt(t[["elapsed"]], 30)
})


test_that("placeholder.csv is the block's output for the sample", {
  # The demo shows sample-data/placeholder.csv in place of the block's Data output: it must stay identical.
  out <- expect_committed(run(rda_file = rdata))$outputs[[1]]
  as_text <- function(x) {
    if (inherits(x, "POSIXct")) x <- format(x, "%Y-%m-%d", tz = "UTC")
    if (is.logical(x)) x <- ifelse(x, "true", "false")
    x <- as.character(x)
    ifelse(is.na(x), "", x)
  }
  placeholder <- utils::read.csv(file.path(BLOCK_DIR, "sample-data", "placeholder.csv"), colClasses = "character",
                                 check.names = FALSE, na.strings = character(0), encoding = "UTF-8")
  expect_equal(names(placeholder), names(out))
  for (n in names(out)) expect_equal(placeholder[[n]], as_text(out[[n]]), info = n)
})
