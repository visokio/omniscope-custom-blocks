# Unit tests for the FlightStats Airlines block, run with the stand-in Omniscope R API and invented answers
# (tests/canned, written by tests/make_canned.py); no request leaves the machine:
#   Rscript tools/r/run-tests.R Connectors/Flightstats/Airlines

canned <- function(name) paste(readLines(file.path(BLOCK_DIR, "tests", "canned", name), warn = FALSE), collapse = "\n")
response <- function(url, status, body) {
  structure(list(url = url, status_code = status, headers = list(`Content-Type` = "application/json"),
                 content = charToRaw(body)), class = "response")
}

# Runs the block with GET replaced by `handler(url)`; returns the result and the URLs requested.
run_mocked <- function(handler, ...) {
  urls <- character(0)
  assign("GET", function(url, ...) { urls <<- c(urls, url); handler(url) }, envir = globalenv())
  on.exit(rm("GET", envir = globalenv()))
  res <- run_block(BLOCK_DIR, list(), list(...))
  res$urls <- urls
  res
}
answer <- function(url) {
  if (grepl("/json/active\\?", url)) return(response(url, 200, canned("active.json")))
  if (grepl("/json/all\\?", url)) return(response(url, 200, canned("all.json")))
  response(url, 404, "{}")
}

test_that("active airlines come out one per record, with the documented fields first", {
  res <- expect_committed(run_mocked(answer, appID = "my-id", appKey = "my-key"))
  out <- res$outputs[[1]]
  expect_equal(nrow(out), 12)
  expect_equal(names(out), c("fs", "iata", "icao", "name", "phoneNumber", "active"))
  expect_equal(out$name[out$fs == "ZQ"], "Kestrel Coastal Airways")
  expect_true(is.na(out$iata[out$fs == "WY*"]))   # no IATA code: empty, not dropped
  expect_true(is.na(out$phoneNumber[out$fs == "QV"]))
  expect_true(is.logical(out$active) && all(out$active))
  expect_match(res$final_message, "12 active airlines")
  expect_equal(length(res$urls), 1)
  expect_match(res$urls, "^https://api.flightstats.com/flex/airlines/rest/v1/json/active\\?appId=my-id&appKey=my-key$")
})

test_that("include inactive asks for the full list", {
  res <- expect_committed(run_mocked(answer, appID = "my-id", appKey = "my-key", includeInactive = TRUE))
  out <- res$outputs[[1]]
  expect_match(res$urls, "/json/all\\?")
  expect_equal(nrow(out), 14)
  expect_equal(sort(out$fs[!out$active]), c("GA*", "PX"))
})

test_that("credentials are URL-encoded", {
  res <- expect_committed(run_mocked(answer, appID = "id with space", appKey = "k&ey=1"))
  expect_match(res$urls, "appId=id%20with%20space&appKey=k%26ey%3D1", fixed = TRUE)
})

test_that("refused credentials stop with FlightStats' message, not an empty output", {
  res <- run_mocked(function(url) response(url, 403, canned("error-403.json")), appID = "x", appKey = "y")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "403: application is not active. Check the App ID and App key.", fixed = TRUE)
  expect_equal(length(res$outputs), 0)
})

test_that("an error answer with status 200 also stops", {
  res <- run_mocked(function(url) response(url, 200, canned("error-403.json")), appID = "x", appKey = "y")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "application is not active")
})

test_that("blank credentials stop before any request", {
  res <- run_mocked(answer, appID = "  ", appKey = "y")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "App ID")
  expect_equal(length(res$urls), 0)
  res <- run_mocked(answer, appID = "x")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "App key")
})

test_that("an empty list gives an empty output with the fields", {
  res <- expect_committed(run_mocked(function(url) response(url, 200, '{"airlines": []}'), appID = "x", appKey = "y"))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(names(res$outputs[[1]]), c("fs", "iata", "icao", "name", "phoneNumber", "active"))
})

test_that("a large list (20,000 airlines) is read", {
  big <- jsonlite::toJSON(list(airlines = data.frame(fs = sprintf("A%05d", 1:20000), name = "Example Air",
                                                     active = TRUE)), auto_unbox = TRUE)
  res <- expect_committed(run_mocked(function(url) response(url, 200, as.character(big)), appID = "x", appKey = "y"))
  expect_equal(nrow(res$outputs[[1]]), 20000)
  expect_true(all(is.na(res$outputs[[1]]$icao)))
})

test_that("invented phone numbers are from ranges reserved for drama and fiction", {
  phones <- read.csv(file.path(BLOCK_DIR, "sample-data", "placeholder.csv"), stringsAsFactors = FALSE)$phoneNumber
  phones <- phones[!is.na(phones) & nzchar(phones)]
  expect_gt(length(phones), 0)
  # Ofcom: 020 7946 0xxx, and 0113, 0117, 0141, 0161 496 0xxx; ComReg (Ireland): 020 91x xxxx
  reserved <- "^\\+44 (20 7946 0|(113|117|141|161) 496 0)\\d{3}$|^\\+353 20 91\\d \\d{4}$"
  expect_true(all(grepl(reserved, phones, perl = TRUE)), info = paste(phones, collapse = ", "))
})
