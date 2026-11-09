# Unit tests for the FlightStats Airports block, run with the stand-in Omniscope R API and invented answers
# (tests/canned, written by tests/make_canned.py); no request leaves the machine:
#   Rscript tools/r/run-tests.R Connectors/Flightstats/Airports

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

AIRPORT_FIELDS <- c("fs", "iata", "icao", "faa", "name", "street1", "street2", "city", "cityCode", "stateCode",
                    "postalCode", "countryCode", "countryName", "regionName", "timeZoneRegionName", "weatherZone",
                    "localTime", "utcOffsetHours", "latitude", "longitude", "elevationFeet", "classification",
                    "active", "delayIndexUrl", "weatherUrl")

test_that("active airports come out one per record, with every documented field in a fixed order", {
  res <- expect_committed(run_mocked(answer, appID = "my-id", appKey = "my-key"))
  out <- res$outputs[[1]]
  expect_equal(nrow(out), 10)
  expect_equal(names(out), AIRPORT_FIELDS)
  kqb <- out[out$fs == "KQB", ]
  expect_equal(kqb$name, "Kestrel Bay Airport")
  expect_equal(kqb$latitude, 54.61234)
  expect_true(is.numeric(out$elevationFeet) && is.numeric(out$utcOffsetHours))
  expect_true(is.na(out$iata[out$fs == "TFD"]))   # no IATA code: empty, not dropped
  expect_true(all(is.na(out$faa)))                # in no answer: still a field
  expect_s3_class(out$localTime, "POSIXct")
  expect_equal(format(out$localTime[out$fs == "ORB"], "%Y-%m-%d %H:%M", tz = "UTC"), "2026-11-06 11:15")
  expect_match(res$final_message, "10 active airports")
  expect_match(res$urls, "^https://api.flightstats.com/flex/airports/rest/v1/json/active\\?appId=my-id&appKey=my-key$")
})

test_that("include inactive asks for the full list", {
  res <- expect_committed(run_mocked(answer, appID = "my-id", appKey = "my-key", includeInactive = TRUE))
  out <- res$outputs[[1]]
  expect_match(res$urls, "/json/all\\?")
  expect_equal(nrow(out), 11)
  expect_equal(out$fs[!out$active], "PNH")
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
  res <- expect_committed(run_mocked(function(url) response(url, 200, '{"airports": []}'), appID = "x", appKey = "y"))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(names(res$outputs[[1]]), AIRPORT_FIELDS)
})

test_that("a large list (20,000 airports) is read", {
  big <- jsonlite::toJSON(list(airports = data.frame(fs = sprintf("A%05d", 1:20000), name = "Example Field",
                                                     latitude = 50, longitude = -1, active = TRUE)), auto_unbox = TRUE)
  res <- expect_committed(run_mocked(function(url) response(url, 200, as.character(big)), appID = "x", appKey = "y"))
  expect_equal(nrow(res$outputs[[1]]), 20000)
  expect_true(all(is.na(res$outputs[[1]]$icao)))
})
