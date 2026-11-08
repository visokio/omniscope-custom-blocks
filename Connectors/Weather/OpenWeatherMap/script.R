library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

library(httr)
library(jsonlite)

# An option that is not set, or set to empty text, is NULL.
option <- function(name) {
  value <- get.option(omni.api, name)
  if (is.null(value) || length(value) == 0 || all(is.na(value))) return(NULL)
  if (is.character(value) && !nzchar(trimws(value[1]))) return(NULL)
  value
}

appid <- option("appid")
apiChoice <- option("apiChoice")
searchChoice <- option("searchChoice")
unitsChoice <- option("unitsChoice")

latitude.field <- option("latitudeField")
longitude.field <- option("longitudeField")
city.field <- option("cityField")
state.field <- option("stateField")
postcode.field <- option("postcodeField")
country.field <- option("countryField")
index.field <- option("indexField")

apply.rate.limit <- isTRUE(get.option(omni.api, "applyRateLimit"))


### Checks

if (is.null(input.data)) abort(omni.api, "Connect an input with one record per location.")
if (is.null(appid)) abort(omni.api, "Enter your OpenWeatherMap API key in 'API key'.")
if (is.null(apiChoice)) apiChoice <- "CURRENT"
if (is.null(searchChoice)) searchChoice <- "LATLON"
if (!(apiChoice %in% c("CURRENT", "FORECAST"))) abort(omni.api, paste0("Unknown weather type '", apiChoice, "'."))
if (!(searchChoice %in% c("LATLON", "CITY", "POSTCODE"))) abort(omni.api, paste0("Unknown search '", searchChoice, "'."))

require.field <- function(field, title) {
  if (is.null(field)) abort(omni.api, paste0("Choose the ", title, " for this search."))
  if (!(field %in% names(input.data))) abort(omni.api, paste0("The ", title, " '", field, "' is not in the input."))
}
optional.field <- function(field, title) {
  if (!is.null(field) && !(field %in% names(input.data))) {
    abort(omni.api, paste0("The ", title, " '", field, "' is not in the input."))
  }
}

if (searchChoice == "LATLON") {
  require.field(latitude.field, "latitude field")
  require.field(longitude.field, "longitude field")
  for (f in c(latitude.field, longitude.field)) {
    x <- input.data[[f]]
    if (!is.numeric(x)) {
      x <- suppressWarnings(as.numeric(as.character(x)))
      if (all(is.na(x)) && any(!is.na(input.data[[f]]))) abort(omni.api, paste0("The field '", f, "' must hold numbers."))
    }
    input.data[[f]] <- x
  }
} else if (searchChoice == "CITY") {
  require.field(city.field, "city field")
  optional.field(state.field, "state field")
  optional.field(country.field, "country code field")
} else {
  require.field(postcode.field, "postcode field")
  optional.field(country.field, "country code field")
}
optional.field(index.field, "field to identify records")


### Requests

base.url <- "https://api.openweathermap.org/data/2.5"
endpoint <- paste(base.url, if (apiChoice == "CURRENT") "weather" else "forecast", sep = "/")
units <- if (identical(unitsChoice, "CELSIUS")) "metric" else if (identical(unitsChoice, "FAHRENHEIT")) "imperial" else NULL

# Text value of a field in record i, or NULL when the field is not chosen or the value is missing or blank.
text.value <- function(field, i) {
  if (is.null(field)) return(NULL)
  v <- input.data[[field]][i]
  if (is.na(v)) return(NULL)
  v <- trimws(as.character(v))
  if (!nzchar(v)) NULL else v
}

# The query for record i, or NULL when the record has no location.
search.query <- function(i) {
  if (searchChoice == "LATLON") {
    lat <- input.data[[latitude.field]][i]
    lon <- input.data[[longitude.field]][i]
    if (is.na(lat) || is.na(lon)) return(NULL)
    return(list(lat = format(lat, digits = 15), lon = format(lon, digits = 15)))
  }
  if (searchChoice == "CITY") {
    city <- text.value(city.field, i)
    if (is.null(city)) return(NULL)
    return(list(q = paste(c(city, text.value(state.field, i), text.value(country.field, i)), collapse = ",")))
  }
  postcode <- text.value(postcode.field, i)
  if (is.null(postcode)) return(NULL)
  list(zip = paste(c(postcode, text.value(country.field, i)), collapse = ","))
}

rate.limit.seconds <- 1.1   # the free plan allows 60 calls a minute
last.call <- NULL
wait.for.rate.limit <- function() {
  if (!apply.rate.limit) return(invisible())
  if (!is.null(last.call)) {
    wait <- rate.limit.seconds - as.numeric(difftime(Sys.time(), last.call, units = "secs"))
    if (wait > 0) Sys.sleep(wait)
  }
  last.call <<- Sys.time()
}

api.message <- function(result) {
  m <- tryCatch(fromJSON(content(result, "text", encoding = "UTF-8"))$message, error = function(e) NULL)
  if (is.null(m) || !length(m)) "" else as.character(m[1])
}

# Calls OpenWeatherMap; returns the parsed answer, or the HTTP status code (a number) when there is no answer.
call.api <- function(query) {
  url <- modify_url(endpoint, query = c(query, if (!is.null(units)) list(units = units), list(appid = appid)))
  for (attempt in 1:4) {
    wait.for.rate.limit()
    result <- tryCatch(GET(url), error = function(e) e)
    if (inherits(result, "error")) return(-1)
    status <- result$status_code
    if (status == 429 && attempt < 4) {
      update.message(omni.api, "OpenWeatherMap's call limit reached: waiting a minute before trying again.")
      Sys.sleep(60)
      next
    }
    if (status == 401) {
      abort(omni.api, paste("OpenWeatherMap refused the API key (401):", api.message(result)))
    }
    if (status == 429) abort(omni.api, paste("OpenWeatherMap's call limit was still exceeded after 3 minutes (429):", api.message(result)))
    if (status != 200) return(status)
    return(fromJSON(content(result, "text", encoding = "UTF-8"), simplifyVector = FALSE))
  }
}


### Answers to records

# The value at a path in a parsed answer, or NA of the given type.
value.at <- function(x, path, type) {
  for (p in path) {
    if (is.null(x) || !is.list(x)) break
    x <- if (is.numeric(p)) (if (length(x) >= p) x[[p]] else NULL) else x[[p]]
  }
  if (is.null(x) || is.list(x) || !length(x)) {
    return(switch(type, num = NA_real_, text = NA_character_, date = as.POSIXct(NA_real_, origin = "1970-01-01", tz = "UTC")))
  }
  switch(type,
         num = as.numeric(x),
         text = as.character(x),
         date = as.POSIXct(as.numeric(x), origin = "1970-01-01", tz = "UTC"))
}

# Output field name, path in the answer, type. Every record gets every field, whatever the weather.
current.fields <- list(
  list("coord.lon", c("coord", "lon"), "num"), list("coord.lat", c("coord", "lat"), "num"),
  list("weather.id", list("weather", 1, "id"), "num"), list("weather.main", list("weather", 1, "main"), "text"),
  list("weather.description", list("weather", 1, "description"), "text"),
  list("weather.icon", list("weather", 1, "icon"), "text"),
  list("base", "base", "text"),
  list("main.temp", c("main", "temp"), "num"), list("main.feels_like", c("main", "feels_like"), "num"),
  list("main.temp_min", c("main", "temp_min"), "num"), list("main.temp_max", c("main", "temp_max"), "num"),
  list("main.pressure", c("main", "pressure"), "num"), list("main.humidity", c("main", "humidity"), "num"),
  list("main.sea_level", c("main", "sea_level"), "num"), list("main.grnd_level", c("main", "grnd_level"), "num"),
  list("visibility", "visibility", "num"),
  list("wind.speed", c("wind", "speed"), "num"), list("wind.deg", c("wind", "deg"), "num"),
  list("wind.gust", c("wind", "gust"), "num"),
  list("clouds.all", c("clouds", "all"), "num"),
  list("rain.1h", c("rain", "1h"), "num"), list("snow.1h", c("snow", "1h"), "num"),
  list("dt", "dt", "date"),
  list("sys.type", c("sys", "type"), "num"), list("sys.id", c("sys", "id"), "num"),
  list("sys.country", c("sys", "country"), "text"),
  list("sys.sunrise", c("sys", "sunrise"), "date"), list("sys.sunset", c("sys", "sunset"), "date"),
  list("timezone", "timezone", "num"), list("id", "id", "num"), list("name", "name", "text")
)

forecast.fields <- list(
  list("dt", "dt", "date"), list("visibility", "visibility", "num"), list("pop", "pop", "num"),
  list("dt_txt", "dt", "date"),
  list("main.temp", c("main", "temp"), "num"), list("main.feels_like", c("main", "feels_like"), "num"),
  list("main.temp_min", c("main", "temp_min"), "num"), list("main.temp_max", c("main", "temp_max"), "num"),
  list("main.pressure", c("main", "pressure"), "num"), list("main.sea_level", c("main", "sea_level"), "num"),
  list("main.grnd_level", c("main", "grnd_level"), "num"), list("main.humidity", c("main", "humidity"), "num"),
  list("main.temp_kf", c("main", "temp_kf"), "num"),
  list("clouds.all", c("clouds", "all"), "num"),
  list("wind.speed", c("wind", "speed"), "num"), list("wind.deg", c("wind", "deg"), "num"),
  list("wind.gust", c("wind", "gust"), "num"),
  list("sys.pod", c("sys", "pod"), "text"),
  list("snow.3h", c("snow", "3h"), "num"), list("rain.3h", c("rain", "3h"), "num"),
  list("id", list("weather", 1, "id"), "num"), list("main", list("weather", 1, "main"), "text"),
  list("description", list("weather", 1, "description"), "text"), list("icon", list("weather", 1, "icon"), "text")
)

fields <- if (apiChoice == "CURRENT") current.fields else forecast.fields

to.records <- function(items) {
  cols <- lapply(fields, function(f) {
    v <- lapply(items, value.at, path = f[[2]], type = f[[3]])
    if (f[[3]] == "date") as.POSIXct(unlist(v), origin = "1970-01-01", tz = "UTC") else unlist(v)
  })
  names(cols) <- vapply(fields, `[[`, "", 1)
  if (!length(items)) {
    cols <- lapply(fields, function(f) value.at(NULL, f[[2]], f[[3]])[0])
    names(cols) <- vapply(fields, `[[`, "", 1)
  }
  as.data.frame(cols, stringsAsFactors = FALSE, check.names = FALSE)
}

# The input values written beside each answer, so records can be traced to their location.
location.fields <- function(i, n) {
  pick <- function(field) {
    v <- if (is.null(i)) input.data[[field]][0] else input.data[[field]][i]
    rep(v, n)
  }
  out <- list()
  if (searchChoice == "LATLON") {
    out$latitude <- pick(latitude.field)
    out$longitude <- pick(longitude.field)
  } else if (searchChoice == "CITY") {
    out$city <- pick(city.field)
    if (!is.null(state.field)) out$state <- pick(state.field)
    if (!is.null(country.field)) out$country <- pick(country.field)
  } else {
    out$postcode <- pick(postcode.field)
    if (!is.null(country.field)) out$country <- pick(country.field)
  }
  if (!is.null(index.field)) out$index <- pick(index.field)
  as.data.frame(out, stringsAsFactors = FALSE, check.names = FALSE)
}

records <- list()
answers <- list()   # one call per distinct query
skipped <- 0
not.found <- 0
failed <- 0

for (i in seq_len(nrow(input.data))) {
  query <- search.query(i)
  if (is.null(query)) {
    skipped <- skipped + 1
    next
  }
  key <- paste(names(query), unlist(query), sep = "=", collapse = "&")
  if (is.null(answers[[key]])) {
    answer <- call.api(query)
    if (!is.numeric(answer)) answer <- to.records(if (apiChoice == "CURRENT") list(answer) else answer$list)
    answers[[key]] <- list(answer)
  }
  weather <- answers[[key]][[1]]
  if (is.numeric(weather)) {
    if (weather == 404) not.found <- not.found + 1 else failed <- failed + 1
    next
  }
  if (!nrow(weather)) next
  records[[length(records) + 1]] <- cbind(weather, location.fields(i, nrow(weather)))
}

output.data <- if (length(records)) as.data.frame(data.table::rbindlist(records)) else cbind(to.records(list()), location.fields(NULL, 0))
rownames(output.data) <- NULL

write.output.records(omni.api, output.data, output.number=1)

message <- paste0("Weather for ", length(records), " of ", nrow(input.data), " input records.")
if (skipped) message <- paste0(message, " ", skipped, " had no location and ", if (skipped == 1) "was" else "were",
                                " skipped.")
if (not.found) message <- paste0(message, " ", not.found, " not found by OpenWeatherMap.")
if (failed) message <- paste0(message, " ", failed, " failed (network or server error).")
close(omni.api, message)
