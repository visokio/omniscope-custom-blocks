# Runs the unit tests of every R block: each tests/test_*.R under the repository, with testthat.
# The tests use the stand-in Omniscope R API in tools/r/harness.R.
#
#   Rscript tools/r/run-tests.R                              # every R block
#   Rscript tools/r/run-tests.R Preparation/Join/Fuzzy-Join  # one block (or several)
#
# Needs R with testthat, jsonlite and the packages the blocks load (Fuzzy-Join: data.table).
# Exits non-zero when a test fails, so it can run in CI.

suppressPackageStartupMessages(library(testthat))

args <- commandArgs(trailingOnly = TRUE)
file_arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
root <- normalizePath(file.path(dirname(sub("^--file=", "", file_arg)), "..", ".."))
setwd(root)

dirs <- if (length(args)) args else "."
files <- unlist(lapply(dirs, function(d) {
  list.files(d, pattern = "^test_.*\\.R$", recursive = TRUE, full.names = TRUE)
}))
files <- files[grepl("(^|/)tests/test_[^/]*\\.R$", files) & !grepl("node_modules|/_site/|/_bundle/", files)]
if (!length(files)) stop("no R tests found under ", paste(dirs, collapse = ", "))

harness <- file.path(root, "tools", "r", "harness.R")
failed <- FALSE
for (f in files) {
  cat("==", f, "\n")
  env <- new.env(parent = globalenv())
  sys.source(harness, envir = env)
  env$BLOCK_DIR <- normalizePath(dirname(dirname(f)))
  res <- as.data.frame(test_file(f, env = env, reporter = "summary", stop_on_failure = FALSE))
  if (any(res$failed > 0) || any(res$error)) failed <- TRUE
}
if (failed) quit(status = 1)
