library(omniscope.api)
library(httr)
library(jsonlite)

omni.api = omniscope.api()

app.id <- get.option(omni.api, "appID")
app.key <- get.option(omni.api, "appKey")
include.inactive <- isTRUE(get.option(omni.api, "includeInactive"))

blank <- function(x) is.null(x) || length(x) == 0 || is.na(x[1]) || trimws(x[1]) == ""
if (blank(app.id)) abort(omni.api, "Enter the App ID of your FlightStats (Cirium Flex) account.")
if (blank(app.key)) abort(omni.api, "Enter the App key of your FlightStats (Cirium Flex) account.")

# The Flex API answers errors as {"error": {"httpStatusCode", "errorCode", "errorMessage"}}
flex.error <- function(result) {
  text <- tryCatch(content(result, "text", encoding = "UTF-8"), error = function(e) "")
  json <- tryCatch(fromJSON(text), error = function(e) NULL)
  msg <- if (is.list(json) && is.list(json$error)) json$error$errorMessage else NULL
  paste0("FlightStats answered ", result$status_code,
         if (!is.null(msg)) paste0(": ", msg) else "",
         if (result$status_code %in% c(401, 403)) ". Check the App ID and App key." else "")
}

url <- modify_url("https://api.flightstats.com",
                  path = paste0("flex/airlines/rest/v1/json/", if (include.inactive) "all" else "active"),
                  query = list(appId = trimws(app.id), appKey = trimws(app.key)))
result <- GET(url)
if (result$status_code != 200) abort(omni.api, flex.error(result))

json <- fromJSON(content(result, "text", encoding = "UTF-8"), flatten = TRUE)
if (is.list(json$error)) abort(omni.api, flex.error(result))

# The documented fields, always present and in this order (an answer may leave some out); any others follow
fields <- c(fs = "text", iata = "text", icao = "text", name = "text", phoneNumber = "text", active = "logical")
airlines <- json$airlines
if (!is.data.frame(airlines)) airlines <- data.frame(row.names = integer(0))
empty <- list(text = NA_character_, logical = NA, number = NA_real_)
for (f in names(fields)) if (!(f %in% names(airlines))) airlines[[f]] <- rep(empty[[fields[[f]]]], nrow(airlines))
airlines <- airlines[, c(names(fields), setdiff(names(airlines), names(fields))), drop = FALSE]
# a list value (an array in the answer) cannot be written: join it as text
for (f in names(airlines)) if (is.list(airlines[[f]])) {
  airlines[[f]] <- vapply(airlines[[f]], function(v) paste(unlist(v), collapse = ", "), "")
}

write.output.records(omni.api, airlines, output.number = 1)
close(omni.api, paste(nrow(airlines), if (include.inactive) "airlines (active and inactive)." else "active airlines."))
