# Unit tests for the Rds Batch Append block, run with the stand-in Omniscope R API:
#   Rscript tools/r/run-tests.R Inputs/Rds-Batch-Append
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

sample_folder <- file.path(BLOCK_DIR, "sample-data", "monthly-sales")

run <- function(..., input = NULL) {
  run_block(BLOCK_DIR, if (is.null(input)) list() else list(input), list(...))
}

# A fresh folder holding the given data frames as .rds files (named by the list names).
make_folder <- function(frames, sub = NULL) {
  dir <- tempfile("rds-")
  dir.create(dir)
  target <- if (is.null(sub)) dir else file.path(dir, sub)
  dir.create(target, showWarnings = FALSE, recursive = TRUE)
  for (n in names(frames)) saveRDS(frames[[n]], file.path(target, n))
  dir
}

test_that("the sample folder appends with scan first (the default), filling the field one month lacks", {
  res <- expect_committed(run(folder = sample_folder))
  out <- res$outputs[[1]]
  expect_equal(nrow(out), 16)
  expect_equal(names(out), c("Branch", "Month", "Orders", "Revenue", "Returns"))
  expect_type(out$Branch, "character")
  expect_s3_class(out$Month, "POSIXct")
  expect_equal(format(unique(out$Month), tz = "UTC"), c("2025-01-01", "2025-02-01", "2025-03-01"))
  expect_equal(sum(is.na(out$Returns)), 10)          # January and February have no Returns
  expect_equal(sum(out$Orders), 4486)
  expect_equal(round(sum(out$Revenue), 2), 191305.3)
  expect_equal(res$final_message, "Appended 3 files, 16 records.")
})

test_that("whole numbers in one file and decimals in another are widened, not cut", {
  dir <- make_folder(list("a.rds" = data.frame(x = 1:2), "b.rds" = data.frame(x = c(2.5, 3.75))))
  out <- expect_committed(run(folder = dir))$outputs[[1]]
  expect_equal(out$x, c(1, 2, 2.5, 3.75))
})

test_that("the sample folder without scan first stops on March, or warns and carries on", {
  res <- run(folder = sample_folder, scanFirst = FALSE)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "sales-2025-03.rds has additional fields, left out: Returns")
  res <- expect_committed(run(folder = sample_folder, scanFirst = FALSE, actionAdditionalFields = "WARN",
                              actionIncorrectFieldType = "WARN"))
  out <- res$outputs[[1]]
  expect_equal(nrow(out), 16)
  expect_equal(names(out), c("Branch", "Month", "Orders", "Revenue"))
  expect_type(out$Orders, "integer")
  expect_match(res$final_message, "Returns")
  expect_match(res$final_message, "field 'Orders' is float, expected int")
})

test_that("logical fields append", {
  dir <- make_folder(list("a.rds" = data.frame(id = 1:2, ok = c(TRUE, FALSE)),
                          "b.rds" = data.frame(id = 3L, ok = NA)))
  out <- expect_committed(run(folder = dir, scanFirst = FALSE))$outputs[[1]]
  expect_equal(out$ok, c(TRUE, FALSE, NA))
})

test_that("only .rds files are read, in any case, and subfolders only when recursive", {
  dir <- make_folder(list("a.rds" = data.frame(x = 1L), "B.RDS" = data.frame(x = 2L)))
  writeLines("not an rds file", file.path(dir, "cards.csv"))
  sub <- file.path(dir, "older"); dir.create(sub)
  saveRDS(data.frame(x = 3L), file.path(sub, "c.rds"))
  expect_equal(expect_committed(run(folder = dir, recursive = TRUE))$outputs[[1]]$x, c(1L, 2L, 3L))
  expect_equal(expect_committed(run(folder = dir, recursive = FALSE))$outputs[[1]]$x, c(1L, 2L))
})

test_that("without scan first, Display warning fills or drops fields and reports them", {
  dir <- make_folder(list("1.rds" = data.frame(a = 1L, b = "x"),
                          "2.rds" = data.frame(a = 2L),
                          "3.rds" = data.frame(a = 3L, b = "z", c = 9)))
  res <- expect_committed(run(folder = dir, scanFirst = FALSE,
                              actionMissingFields = "WARN", actionAdditionalFields = "WARN"))
  out <- res$outputs[[1]]
  expect_equal(names(out), c("a", "b"))
  expect_equal(out$b, c("x", NA, "z"))
  expect_match(res$final_message, "2.rds is missing fields: b")
  expect_match(res$final_message, "3.rds has additional fields, left out: c")
  expect_true(length(res$messages) > 0)
})

test_that("without scan first, Silently ignore does the same with no warning", {
  dir <- make_folder(list("1.rds" = data.frame(a = 1L, b = "x"), "2.rds" = data.frame(a = 2L, c = 1)))
  res <- expect_committed(run(folder = dir, scanFirst = FALSE,
                              actionMissingFields = "IGNORE", actionAdditionalFields = "IGNORE"))
  expect_equal(names(res$outputs[[1]]), c("a", "b"))
  expect_equal(res$final_message, "Appended 2 files, 2 records.")
})

test_that("without scan first, Stop with an error (the default) stops on a missing or extra field", {
  dir <- make_folder(list("1.rds" = data.frame(a = 1L, b = "x"), "2.rds" = data.frame(a = 2L)))
  res <- run(folder = dir, scanFirst = FALSE)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "is missing fields: b")
  dir <- make_folder(list("1.rds" = data.frame(a = 1L), "2.rds" = data.frame(a = 2L, b = "y")))
  res <- run(folder = dir, scanFirst = FALSE)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "has additional fields")
})

test_that("a field of another type is converted, with a warning, or stops the block", {
  dir <- make_folder(list("1.rds" = data.frame(id = 1L, code = "A1"), "2.rds" = data.frame(id = "7", code = 42)))
  res <- expect_committed(run(folder = dir, actionIncorrectFieldType = "WARN"))
  out <- res$outputs[[1]]
  expect_equal(out$id, c(1L, 7L))
  expect_equal(out$code, c("A1", "42"))
  expect_match(res$final_message, "field 'id' is text, expected int")
  res <- run(folder = dir)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "field 'id' is text, expected int")
})

test_that("text dates are converted to date-times when the schema says so", {
  dir <- make_folder(list("1.rds" = data.frame(d = as.POSIXct("2025-01-02 10:00", tz = "UTC")),
                          "2.rds" = data.frame(d = "2025-02-03")))
  out <- expect_committed(run(folder = dir, actionIncorrectFieldType = "IGNORE"))$outputs[[1]]
  expect_s3_class(out$d, "POSIXct")
  expect_equal(format(out$d, "%Y-%m-%d", tz = "UTC"), c("2025-01-02", "2025-02-03"))
})

test_that("the source field holds each record's file, under the chosen name", {
  res <- expect_committed(run(folder = sample_folder, addSourceField = TRUE, sourceFieldName = "File"))
  out <- res$outputs[[1]]
  expect_equal(names(out)[6], "File")
  expect_equal(as.vector(table(basename(out$File))), c(5L, 5L, 6L))
  out <- expect_committed(run(folder = sample_folder, addSourceField = TRUE, sourceFieldName = ""))$outputs[[1]]
  expect_true("Source" %in% names(out))
  res <- run(folder = sample_folder, addSourceField = TRUE, sourceFieldName = "Branch")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "already have a field called 'Branch'")
})

test_that("file paths can come from an input field; missing paths are skipped", {
  files <- sort(list.files(sample_folder, full.names = TRUE))
  input <- data.frame(Path = c(files[1], NA, files[3]), stringsAsFactors = FALSE)
  out <- expect_committed(run(input = input, pathField = "Path", folder = "/ignored"))$outputs[[1]]
  expect_equal(nrow(out), 11)
  res <- run(input = input)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Path field")
})

test_that("an empty data frame in one file adds no records", {
  dir <- make_folder(list("1.rds" = data.frame(a = integer(0), b = character(0)), "2.rds" = data.frame(a = 1L, b = "x")))
  out <- expect_committed(run(folder = dir))$outputs[[1]]
  expect_equal(nrow(out), 1)
  expect_equal(names(out), c("a", "b"))
})

test_that("problems with the folder or the files stop with a clear message", {
  res <- run(folder = file.path(tempdir(), "no-such-folder"))
  expect_match(res$final_message, "Folder not found")
  res <- run(folder = make_folder(list()))
  expect_match(res$final_message, "No .rds files in")
  res <- run_block(BLOCK_DIR, list(), list())
  expect_match(res$final_message, "Choose a folder")
  dir <- make_folder(list("a.rds" = list(1, 2)))
  res <- run(folder = dir)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "holds a list, not a data frame")
  dir <- make_folder(list("a.rds" = data.frame(x = 1L)))
  writeLines("garbage", file.path(dir, "b.rds"))
  res <- run(folder = dir)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Could not read .*b.rds as a .rds file")
})

test_that("100 files of 2,000 records append in seconds", {
  frames <- lapply(1:100, function(i) data.frame(id = seq_len(2000) + i * 2000L, g = factor(sample(letters, 2000, TRUE)),
                                                 v = runif(2000)))
  names(frames) <- sprintf("part-%03d.rds", 1:100)
  dir <- make_folder(frames)
  t <- system.time(res <- run(folder = dir))
  expect_committed(res)
  expect_equal(nrow(res$outputs[[1]]), 200000)
  expect_equal(res$final_message, "Appended 100 files, 200,000 records.")
  expect_lt(t[["elapsed"]], 60)
})


test_that("placeholder.csv is the block's output for the sample", {
  # The demo shows sample-data/placeholder.csv in place of the block's Appended output: it must stay identical.
  out <- expect_committed(run(folder = sample_folder, recursive = TRUE, scanFirst = TRUE, addSourceField = FALSE))$outputs[[1]]
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
