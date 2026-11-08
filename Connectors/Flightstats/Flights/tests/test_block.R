# Unit tests for the FlightStats Flights block, run with the stand-in Omniscope R API and invented schedule
# answers (tests/canned, written by tests/make_canned.py); no request leaves the machine:
#   Rscript tools/r/run-tests.R Connectors/Flightstats/Flights

bookings <- file.path(BLOCK_DIR, "sample-data", "flight-bookings.csv")
canned_dir <- file.path(BLOCK_DIR, "tests", "canned")
read_text <- function(path) paste(readLines(path, warn = FALSE), collapse = "\n")
response <- function(url, status, body) {
  structure(list(url = url, status_code = status, headers = list(`Content-Type` = "application/json"),
                 content = charToRaw(body)), class = "response")
}

# The schedules answer for a request URL: the canned file for that flight and day, else no flights.
schedules <- function(url) {
  m <- regmatches(url, regexec("/json/flight/([^/]+)/([^/]+)/departing/(\\d+)/(\\d+)/(\\d+)\\?", url))[[1]]
  if (!length(m)) return(response(url, 404, "{}"))
  f <- file.path(canned_dir, "schedules", sprintf("%s-%s-%s-%02d-%02d.json", m[2], m[3], m[4],
                                                  as.integer(m[5]), as.integer(m[6])))
  if (file.exists(f)) return(response(url, 200, read_text(f)))
  response(url, 200, '{"request": {}, "scheduledFlights": [], "appendix": {}}')
}

run_mocked <- function(input, handler = schedules, ...) {
  urls <- character(0)
  assign("GET", function(url, ...) { urls <<- c(urls, url); handler(url) }, envir = globalenv())
  on.exit(rm("GET", envir = globalenv()))
  opts <- modifyList(list(appID = "my-id", appKey = "my-key", carrierField = "Carrier",
                          flightNumberField = "Flight", dateField = "Departure date"), list(...))
  res <- run_block(BLOCK_DIR, if (is.null(input)) list() else list(input), opts)
  res$urls <- urls
  res
}

FIELDS <- c("Requested carrier", "Requested flight number", "Requested date", "carrierFsCode", "flightNumber",
            "departureAirportFsCode", "arrivalAirportFsCode", "departureTime", "arrivalTime", "stops",
            "departureTerminal", "arrivalTerminal", "flightEquipmentIataCode", "isCodeshare", "isWetlease",
            "serviceType", "serviceClasses", "trafficRestrictions", "codeshares", "referenceCode")

test_that("the sample bookings give one record per scheduled leg, with the request to join back on", {
  res <- expect_committed(run_mocked(bookings))
  out <- res$outputs[[1]]
  expect_equal(names(out), FIELDS)
  expect_equal(nrow(out), 8)    # 7 flights found, TF77 has two legs; QV931 not in the schedules
  expect_equal(length(res$urls), 8)   # 10 bookings: ZQ214 twice (one request), RB with no number skipped
  expect_match(res$final_message,
               "8 scheduled flights for 8 distinct requests; 1 not in the schedules; 1 input records skipped")
  zq <- out[out$carrierFsCode == "ZQ", ]
  expect_equal(zq[["Requested flight number"]], "214")
  expect_equal(format(zq[["Requested date"]], "%Y-%m-%d", tz = "UTC"), "2026-11-16")
  expect_equal(format(zq$departureTime, "%Y-%m-%d %H:%M", tz = "UTC"), "2026-11-16 07:10")
  expect_equal(zq$departureAirportFsCode, "KQB")
  expect_equal(zq$codeshares, "XK5214")
  expect_equal(zq$serviceClasses, "Y, J")
  expect_true(is.na(zq$arrivalTerminal))
  tf <- out[out$carrierFsCode == "TF", ]
  expect_equal(paste(tf$departureAirportFsCode, tf$arrivalAirportFsCode), c("RBK TFD", "TFD HBL"))
  j7 <- out[out$carrierFsCode == "J7", ]
  expect_equal(j7$codeshares, "XK1402, OY7402")
  expect_true(j7$isCodeshare)
  expect_equal(j7$trafficRestrictions, "Q")
  expect_true(is.integer(out$stops) && is.logical(out$isWetlease))
})

test_that("no list fields reach the output", {
  out <- expect_committed(run_mocked(bookings))$outputs[[1]]
  expect_false(any(vapply(out, is.list, TRUE)))
})

test_that("the request URL carries the flight, the day and the encoded credentials", {
  res <- expect_committed(run_mocked(bookings, appKey = "k&y"))
  expect_true(paste0("https://api.flightstats.com/flex/schedules/rest/v1/json/flight/ZQ/214/departing/2026/11/16",
                     "?appId=my-id&appKey=k%26y") %in% res$urls)
})

test_that("an empty input gives an empty output with the fields, and no requests", {
  empty <- read.csv(bookings, stringsAsFactors = FALSE, check.names = FALSE)[0, ]
  empty[["Departure date"]] <- as.POSIXct(character(0), tz = "UTC")
  res <- expect_committed(run_mocked(empty))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(names(res$outputs[[1]]), FIELDS)
  expect_equal(length(res$urls), 0)
})

test_that("refused credentials stop with FlightStats' message instead of an empty result", {
  refused <- function(url) response(url, 403, read_text(file.path(canned_dir, "error-403.json")))
  res <- run_mocked(bookings, handler = refused)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "403: application is not active. Check the App ID and App key.", fixed = TRUE)
  expect_equal(length(res$urls), 1)
})

test_that("other failed requests are reported and the rest still come out", {
  handler <- function(url) if (grepl("/XK/", url)) response(url, 500, "oops") else schedules(url)
  res <- expect_committed(run_mocked(bookings, handler = handler))
  expect_equal(nrow(res$outputs[[1]]), 6)
  expect_match(res$final_message, "2 failed: XK88 2026-11-17 (FlightStats answered 500)", fixed = TRUE)
})

test_that("a flight number read as a number and a lower-case carrier still work", {
  input <- data.frame(Carrier = "zq", Flight = 214, `Departure date` = "2026-11-16 09:30", check.names = FALSE)
  out <- expect_committed(run_mocked(input))$outputs[[1]]
  expect_equal(nrow(out), 1)
  expect_equal(out[["Requested carrier"]], "ZQ")
})

test_that("wrong field types, missing choices, no credentials or no input stop with a message", {
  input <- data.frame(Carrier = 1L, Flight = 214, `Departure date` = "2026-11-16", check.names = FALSE)
  res <- run_mocked(input)
  expect_equal(res$status, "aborted"); expect_match(res$final_message, "Carrier field")
  input <- data.frame(Carrier = "ZQ", Flight = 214, `Departure date` = "16 Nov", check.names = FALSE)
  res <- run_mocked(input)
  expect_equal(res$status, "aborted"); expect_match(res$final_message, "Date field")
  res <- run_mocked(bookings, flightNumberField = NULL)
  expect_equal(res$status, "aborted"); expect_match(res$final_message, "Flight number field")
  res <- run_mocked(bookings, appKey = "")
  expect_equal(res$status, "aborted"); expect_match(res$final_message, "App key")
  res <- run_mocked(NULL)
  expect_equal(res$status, "aborted"); expect_match(res$final_message, "Connect")
  expect_equal(length(res$urls), 0)
})

test_that("2,000 bookings of 50 flights make 50 requests", {
  set.seed(3)
  keys <- c("ZQ|214|2026-11-16", "XK|88|2026-11-17", "LP|6|2026-11-18", sprintf("QV|%d|2026-11-19", 1:47))
  pick <- strsplit(sample(keys, 2000, TRUE), "|", fixed = TRUE)
  input <- data.frame(Carrier = vapply(pick, `[`, "", 1), Flight = vapply(pick, `[`, "", 2),
                      `Departure date` = vapply(pick, `[`, "", 3), check.names = FALSE)
  res <- expect_committed(run_mocked(input))
  expect_equal(length(res$urls), 50)
  expect_equal(nrow(res$outputs[[1]]), 3)
})
