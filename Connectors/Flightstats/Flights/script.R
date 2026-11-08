library(omniscope.api)
library(httr)
library(jsonlite)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number = 1)

carrier.field <- get.option(omni.api, "carrierField")
number.field <- get.option(omni.api, "flightNumberField")
date.field <- get.option(omni.api, "dateField")
app.id <- get.option(omni.api, "appID")
app.key <- get.option(omni.api, "appKey")

blank <- function(x) is.null(x) || length(x) == 0 || is.na(x[1]) || trimws(x[1]) == ""

# sanity checks
if (is.null(input.data)) abort(omni.api, "Connect the flights to look up to the block's input.")
if (blank(app.id)) abort(omni.api, "Enter the App ID of your FlightStats (Cirium Flex) account.")
if (blank(app.key)) abort(omni.api, "Enter the App key of your FlightStats (Cirium Flex) account.")
choices <- list(c("Carrier field", carrier.field), c("Flight number field", number.field), c("Date field", date.field))
for (f in choices) {
  if (blank(f[2]) || !(f[2] %in% names(input.data))) abort(omni.api, paste0("Choose the ", f[1], "."))
}
if (!is.character(input.data[[carrier.field]])) abort(omni.api, "\"Carrier field\" must be a text field, such as LH.")
if (!inherits(input.data[[date.field]], c("POSIXct", "Date"))) {
  abort(omni.api, "\"Date field\" must be a date field.")
}

# The requested flights: carrier code, flight number (digits only) and departure day, each distinct one once
number.text <- trimws(as.character(input.data[[number.field]]))
number.text <- sub("\\.0+$", "", number.text)  # 1234 read as a decimal number
requests <- data.frame(
  `Requested carrier` = toupper(trimws(input.data[[carrier.field]])),
  `Requested flight number` = number.text,
  `Requested date` = as.POSIXct(format(input.data[[date.field]], "%Y-%m-%d", tz = "UTC"), tz = "UTC"),
  check.names = FALSE, stringsAsFactors = FALSE)
usable <- !is.na(requests[[1]]) & requests[[1]] != "" & grepl("^[0-9]{1,4}$", requests[[2]]) & !is.na(requests[[3]])
skipped <- sum(!usable)
requests <- unique(requests[usable, , drop = FALSE])

# Output fields, always present and in this order
text.fields <- c("carrierFsCode", "flightNumber", "departureAirportFsCode", "arrivalAirportFsCode", "departureTerminal",
                 "arrivalTerminal", "flightEquipmentIataCode", "serviceType", "serviceClasses", "trafficRestrictions",
                 "codeshares", "referenceCode")
fields <- c("Requested carrier", "Requested flight number", "Requested date", "carrierFsCode", "flightNumber",
            "departureAirportFsCode", "arrivalAirportFsCode", "departureTime", "arrivalTime", "stops",
            "departureTerminal", "arrivalTerminal", "flightEquipmentIataCode", "isCodeshare", "isWetlease",
            "serviceType", "serviceClasses", "trafficRestrictions", "codeshares", "referenceCode")

local.time <- function(x) as.POSIXct(substr(as.character(x), 1, 19), tz = "UTC", format = "%Y-%m-%dT%H:%M:%S")
join.text <- function(v) {
  if (is.data.frame(v)) {  # codeshares: objects with carrierFsCode and flightNumber
    if (!nrow(v)) return(NA_character_)
    return(paste(paste0(v$carrierFsCode, v$flightNumber), collapse = ", "))
  }
  v <- unlist(v)
  if (!length(v)) NA_character_ else paste(v, collapse = ", ")
}

tidy <- function(flights, request) {
  n <- nrow(flights)
  out <- data.frame(request[rep(1, n), , drop = FALSE], check.names = FALSE, row.names = NULL)
  col <- function(name) if (name %in% names(flights)) flights[[name]] else rep(NA, n)
  for (f in text.fields) {
    v <- col(f)
    out[[f]] <- if (is.list(v)) vapply(v, join.text, "") else as.character(v)
  }
  out$departureTime <- local.time(col("departureTime"))
  out$arrivalTime <- local.time(col("arrivalTime"))
  out$stops <- as.integer(col("stops"))
  out$isCodeshare <- as.logical(col("isCodeshare"))
  out$isWetlease <- as.logical(col("isWetlease"))
  out[, fields, drop = FALSE]
}

flex.error <- function(result) {
  text <- tryCatch(content(result, "text", encoding = "UTF-8"), error = function(e) "")
  json <- tryCatch(fromJSON(text), error = function(e) NULL)
  msg <- if (is.list(json) && is.list(json$error)) json$error$errorMessage else NULL
  paste0("FlightStats answered ", result$status_code, if (!is.null(msg)) paste0(": ", msg) else "")
}

base <- "https://api.flightstats.com"
results <- list()
not.found <- 0
failed <- character(0)
for (i in seq_len(nrow(requests))) {
  r <- requests[i, , drop = FALSE]
  d <- r[["Requested date"]]
  url <- modify_url(base,
                    path = paste("flex/schedules/rest/v1/json/flight", r[["Requested carrier"]],
                                 r[["Requested flight number"]], "departing",
                                 format(d, "%Y", tz = "UTC"), as.integer(format(d, "%m", tz = "UTC")),
                                 as.integer(format(d, "%d", tz = "UTC")), sep = "/"),
                    query = list(appId = trimws(app.id), appKey = trimws(app.key)))
  result <- GET(url)
  if (result$status_code %in% c(401, 403)) {
    abort(omni.api, paste0(flex.error(result), ". Check the App ID and App key."))
  }
  label <- paste0(r[[1]], r[[2]], " ", format(d, "%Y-%m-%d", tz = "UTC"))
  if (result$status_code != 200) {
    failed <- c(failed, paste0(label, " (", flex.error(result), ")"))
    next
  }
  json <- fromJSON(content(result, "text", encoding = "UTF-8"), flatten = TRUE)
  if (is.list(json$error)) {
    failed <- c(failed, paste0(label, " (", json$error$errorMessage, ")"))
    next
  }
  flights <- json$scheduledFlights
  if (!is.data.frame(flights) || nrow(flights) == 0) {
    not.found <- not.found + 1
    next
  }
  results[[length(results) + 1]] <- tidy(flights, r)
}

empty.request <- data.frame(`Requested carrier` = character(0), `Requested flight number` = character(0),
                            `Requested date` = as.POSIXct(character(0), tz = "UTC"), check.names = FALSE)
output.data <- if (length(results)) {
  do.call(rbind, results)
} else {
  tidy(data.frame(row.names = integer(0)), empty.request)
}
rownames(output.data) <- NULL

message <- paste0(nrow(output.data), " scheduled flights for ", nrow(requests), " distinct requests")
if (not.found) message <- paste0(message, "; ", not.found, " not in the schedules")
if (skipped) message <- paste0(message, "; ", skipped, " input records skipped (missing carrier, number or date)")
if (length(failed)) {
  message <- paste0(message, "; ", length(failed), " failed: ", paste(head(failed, 3), collapse = "; "))
}
write.output.records(omni.api, output.data, output.number = 1)
close(omni.api, paste0(message, "."))
