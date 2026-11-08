# Unit tests for the OpenWeatherMap block, run with the stand-in Omniscope R API and invented responses
# (tests/canned, written by tests/make_canned.R). No call reaches OpenWeatherMap.
#   Rscript tools/r/run-tests.R Connectors/Weather/OpenWeatherMap
# run-tests.R provides run_block(), expect_committed() and BLOCK_DIR (this block's folder).

sites_csv <- file.path(BLOCK_DIR, "sample-data", "sites.csv")
sites <- read.csv(sites_csv, stringsAsFactors = FALSE, check.names = FALSE)
canned <- function(file) paste(readLines(file.path(BLOCK_DIR, "tests", "canned", file), warn = FALSE), collapse = "\n")

http <- new.env()
response <- function(url, status, file) {
  structure(list(url = url, status_code = status, headers = list(`Content-Type` = "application/json"),
                 content = charToRaw(canned(file))), class = "response")
}
# Answers like OpenWeatherMap: the canned answer for the site whose latitude, city or postcode was asked
# for, 404 for anything else. http$queue holds forced answers (status, file) served first.
fake_get <- function(url, ...) {
  http$urls <- c(http$urls, url)
  if (length(http$queue)) {
    next_answer <- http$queue[[1]]
    http$queue <- http$queue[-1]
    return(response(url, next_answer$status, next_answer$file))
  }
  u <- httr::parse_url(url)
  q <- u$query
  kind <- if (grepl("forecast$", u$path)) "forecast" else "current"
  i <- integer(0)
  ok <- !is.na(sites$Latitude)
  if (!is.null(q$lat)) i <- which(ok & abs(sites$Latitude - as.numeric(q$lat)) < 1e-4)
  if (!is.null(q$q)) i <- which(ok & sites$City == strsplit(q$q, ",")[[1]][1])
  if (!is.null(q$zip)) i <- which(ok & sites$Postcode == strsplit(q$zip, ",")[[1]][1])
  if (!length(i)) return(response(url, 404, "error-404.json"))
  response(url, 200, sprintf("%s-%s.json", kind, sites$`Site ID`[i[1]]))
}

run <- function(input = sites_csv, ..., queue = list()) {
  http$urls <- character(0)
  http$sleeps <- numeric(0)
  http$queue <- queue
  assign("GET", fake_get, envir = globalenv())
  assign("Sys.sleep", function(time) http$sleeps <- c(http$sleeps, time), envir = globalenv())
  on.exit(rm(list = c("GET", "Sys.sleep"), envir = globalenv()))
  opts <- list(...)
  if (is.null(opts$appid)) opts$appid <- "test-key"
  inputs <- if (is.null(input)) list() else list(input)
  suppressMessages(run_block(BLOCK_DIR, inputs, opts))
}
latlon <- function(...) run(latitudeField = "Latitude", longitudeField = "Longitude", indexField = "Site ID", ...)
query_of <- function(url) httr::parse_url(url)$query

current_fields <- c("coord.lon", "coord.lat", "weather.id", "weather.main", "weather.description", "weather.icon",
  "base", "main.temp", "main.feels_like", "main.temp_min", "main.temp_max", "main.pressure", "main.humidity",
  "main.sea_level", "main.grnd_level", "visibility", "wind.speed", "wind.deg", "wind.gust", "clouds.all",
  "rain.1h", "snow.1h", "dt", "sys.type", "sys.id", "sys.country", "sys.sunrise", "sys.sunset", "timezone",
  "id", "name")

test_that("current weather by latitude and longitude: one record per located site", {
  res <- expect_committed(latlon(applyRateLimit = FALSE))
  out <- res$outputs[[1]]
  expect_equal(nrow(out), 6)
  expect_equal(names(out), c(current_fields, "latitude", "longitude", "index"))
  expect_equal(out$index, sprintf("S%02d", 1:6))
  expect_equal(out$name, c("Leeds", "Bristol", "Glasgow", "Cardiff", "Norwich", "Belfast"))
  expect_equal(out$weather.main, c("Rain", "Clouds", "Clear", "Mist", "Snow", "Clouds"))
  expect_equal(out$main.temp[1], 11.9)
  expect_equal(out$rain.1h, c(0.42, NA, NA, NA, NA, NA))
  expect_equal(out$snow.1h, c(NA, NA, NA, NA, 0.18, NA))
  expect_equal(out$clouds.all, c(75, 75, 0, 40, 90, 60))
  expect_match(res$final_message, "Weather for 6 of 7 input records. 1 had no location")
  expect_length(http$urls, 6)
  q <- query_of(http$urls[1])
  expect_equal(q[c("lat", "lon", "units", "appid")], list(lat = "53.79648", lon = "-1.54785", units = "metric",
                                                           appid = "test-key"))
})

test_that("latitude and longitude come out as the input's numbers, not text", {
  out <- expect_committed(latlon(applyRateLimit = FALSE))$outputs[[1]]
  expect_true(is.numeric(out$latitude))
  expect_equal(out$latitude, sites$Latitude[1:6])
  expect_equal(out$longitude, sites$Longitude[1:6])
})

test_that("a second weather condition does not duplicate the location (the first is the primary one)", {
  out <- expect_committed(latlon(applyRateLimit = FALSE))$outputs[[1]]
  expect_equal(sum(out$index == "S02"), 1)
  expect_equal(out$weather.description[out$index == "S02"], "broken clouds")
})

test_that("times are date-times in UTC, not Unix seconds", {
  out <- expect_committed(latlon(applyRateLimit = FALSE))$outputs[[1]]
  for (f in c("dt", "sys.sunrise", "sys.sunset")) expect_s3_class(out[[f]], "POSIXct")
  expect_equal(format(out$dt[1], "%Y-%m-%d %H:%M", tz = "UTC"), "2026-11-06 11:58")
  expect_equal(format(out$sys.sunrise[1], "%H:%M", tz = "UTC"), "06:59")
})

test_that("the fields are the same whatever the weather", {
  # Cardiff (S04) is misty, with no rain, snow or gust: rain.1h, snow.1h and wind.gust are still there, empty
  out <- expect_committed(latlon(sites[4, ], applyRateLimit = FALSE))$outputs[[1]]
  expect_equal(names(out), c(current_fields, "latitude", "longitude", "index"))
  expect_true(is.na(out$rain.1h) && is.na(out$snow.1h) && is.na(out$wind.gust))
})

test_that("5-day forecast: 40 three-hourly records per site, times in UTC whatever the server's zone", {
  old <- Sys.getenv("TZ")
  Sys.setenv(TZ = "America/New_York")
  on.exit(Sys.setenv(TZ = old))
  out <- expect_committed(latlon(apiChoice = "FORECAST", applyRateLimit = FALSE))$outputs[[1]]
  expect_equal(nrow(out), 240)
  expect_equal(names(out)[1:4], c("dt", "visibility", "pop", "dt_txt"))
  expect_true(all(c("rain.3h", "snow.3h", "id", "main", "description", "icon") %in% names(out)))
  expect_equal(format(out$dt_txt[1], "%Y-%m-%d %H:%M", tz = "UTC"), "2026-11-06 15:00")
  expect_equal(as.numeric(out$dt_txt), as.numeric(out$dt))
  expect_equal(as.vector(table(out$index)), rep(40, 6))
  expect_match(http$urls[1], "/data/2.5/forecast?", fixed = TRUE)
})

test_that("city search: names with spaces are encoded, missing parts are left out, unknown cities counted", {
  input <- data.frame(Town = c("Leeds", "Milton Keynes", NA), State = NA_character_, Country = c("GB", NA, "GB"))
  res <- expect_committed(run(input, searchChoice = "CITY", cityField = "Town", stateField = "State",
                              countryField = "Country", applyRateLimit = FALSE))
  out <- res$outputs[[1]]
  expect_equal(nrow(out), 1)
  expect_equal(out$city, "Leeds")
  expect_equal(out$country, "GB")
  expect_true("state" %in% names(out))
  expect_length(http$urls, 2)
  expect_equal(query_of(http$urls[1])$q, "Leeds,GB")
  expect_match(http$urls[2], "q=Milton%20Keynes&", fixed = TRUE)
  expect_false(any(grepl("NA", http$urls)))
  expect_match(res$final_message, "1 had no location and was skipped. 1 not found by OpenWeatherMap.")
})

test_that("postcode search sends zip=postcode,country", {
  input <- data.frame(PC = c("BS1", "CF10"), CC = c("GB", "GB"))
  out <- expect_committed(run(input, searchChoice = "POSTCODE", postcodeField = "PC", countryField = "CC",
                              unitsChoice = "FAHRENHEIT", applyRateLimit = FALSE))$outputs[[1]]
  expect_equal(out$name, c("Bristol", "Cardiff"))
  expect_equal(names(out)[32:33], c("postcode", "country"))
  expect_equal(query_of(http$urls[1])[c("zip", "units")], list(zip = "BS1,GB", units = "imperial"))
})

test_that("Kelvin sends no units", {
  expect_committed(latlon(sites[1, ], unitsChoice = "KELVIN", applyRateLimit = FALSE))
  expect_null(query_of(http$urls[1])$units)
})

test_that("the same location is asked for once", {
  input <- sites[c(1, 1, 2, 1), ]
  out <- expect_committed(latlon(input, applyRateLimit = FALSE))$outputs[[1]]
  expect_equal(out$index, c("S01", "S01", "S02", "S01"))
  expect_length(http$urls, 2)
})

test_that("a missing field choice stops with a message rather than failing later", {
  res <- run(searchChoice = "LATLON", latitudeField = "Latitude", applyRateLimit = FALSE)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "longitude field")
  res <- run(searchChoice = "CITY", applyRateLimit = FALSE)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "city field")
  res <- run(searchChoice = "LATLON", latitudeField = "Site", longitudeField = "Longitude", applyRateLimit = FALSE)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "must hold numbers")
  expect_length(http$urls, 0)
})

test_that("a refused API key stops with OpenWeatherMap's message", {
  res <- latlon(applyRateLimit = FALSE, queue = list(list(status = 401, file = "error-401.json")))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "refused the API key \\(401\\): Invalid API key")
  res <- run(appid = "", latitudeField = "Latitude", longitudeField = "Longitude")
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "API key")
})

test_that("over the call limit (429) the block waits a minute and tries again", {
  res <- expect_committed(latlon(sites[1, ], applyRateLimit = FALSE,
                                 queue = list(list(status = 429, file = "error-429.json"))))
  expect_equal(nrow(res$outputs[[1]]), 1)
  expect_equal(http$sleeps, 60)
  res <- latlon(sites[1, ], applyRateLimit = FALSE,
                queue = rep(list(list(status = 429, file = "error-429.json")), 4))
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "429")
})

test_that("the free-plan rate limit spaces the calls out", {
  out <- expect_committed(latlon(applyRateLimit = TRUE))$outputs[[1]]
  expect_equal(nrow(out), 6)
  expect_gte(length(http$sleeps), 5)
  expect_true(all(http$sleeps > 0 & http$sleeps <= 1.1))
})

test_that("empty input gives an empty output with all the fields; no input stops with a message", {
  empty <- sites[0, ]
  res <- expect_committed(latlon(empty, applyRateLimit = FALSE))
  expect_equal(nrow(res$outputs[[1]]), 0)
  expect_equal(names(res$outputs[[1]]), c(current_fields, "latitude", "longitude", "index"))
  res <- latlon(NULL)
  expect_equal(res$status, "aborted")
  expect_match(res$final_message, "Connect an input")
})

test_that("two thousand records over six sites need six calls", {
  input <- sites[rep(1:6, length.out = 2000), ]
  t <- system.time(res <- latlon(input, apiChoice = "FORECAST", applyRateLimit = FALSE))
  expect_committed(res)
  expect_equal(nrow(res$outputs[[1]]), 2000 * 40)
  expect_length(http$urls, 6)
  expect_lt(t[["elapsed"]], 60)
})

test_that("the message agrees in number: 1 record was skipped, 2 records were", {
  input <- data.frame(Town = c("Leeds", NA, NA), Country = "GB")
  res <- expect_committed(run(input, searchChoice = "CITY", cityField = "Town", countryField = "Country",
                              applyRateLimit = FALSE))
  expect_match(res$final_message, "2 had no location and were skipped.", fixed = TRUE)
  res <- expect_committed(run(sites_csv, latitudeField = "Latitude", longitudeField = "Longitude",
                              applyRateLimit = FALSE))
  expect_match(res$final_message, "1 had no location and was skipped.", fixed = TRUE)
})

test_that("invented answers are plausible: snow only near freezing", {
  for (f in list.files(file.path(BLOCK_DIR, "tests", "canned"), "^(current|forecast)-", full.names = TRUE)) {
    d <- jsonlite::fromJSON(f, simplifyVector = FALSE)
    steps <- if (is.null(d$list)) list(d) else d$list
    for (s in steps) if (s$weather[[1]]$main == "Snow") expect_lte(s$main$temp, 2)
  }
  placeholder <- read.csv(file.path(BLOCK_DIR, "sample-data", "placeholder.csv"))
  expect_true(all(placeholder$main.temp[placeholder$weather.main == "Snow"] <= 2))
})
