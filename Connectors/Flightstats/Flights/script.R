library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

### Input fields

flight.carrier.field <-get.option(omni.api, "carrierField")
flight.number.field <- get.option(omni.api, "flightNumberField")
flight.date.field <- get.option(omni.api, "dateField")

### Parameters

flightstats.app.id <- get.option(omni.api, "appID")

flightstats.app.key <- get.option(omni.api, "appKey")

### Script


library(httr)
library(jsonlite)
library(data.table)
library(dplyr)
library(lubridate)

# sanity checks
if (is.null(input.data)) stop("No input data")

# extract relevant fields from data
flights <- data.table(carrier=input.data[, flight.carrier.field], number=input.data[, flight.number.field], date=input.data[, flight.date.field])


app.id.string <- paste("appId", flightstats.app.id, sep="=")
app.key.string <- paste("appKey", flightstats.app.key, sep="=")

app.info <- paste(app.id.string, app.key.string, sep="&")


base <- "https://api.flightstats.com"
endpoint <- "flex/schedules/rest/v1/json/flight"


output.data <- NULL

# iterate through flights and request info from flighstats
for (i in 1:nrow(flights)) {
  
  carrier = flights$carrier[i]
  number = flights$number[i]
  departure.day = day(flights$date[i])
  departure.month = month(flights$date[i])
  departure.year = year(flights$date[i])
  
  # make sure we don't send garbage
  if (is.na(carrier) || is.na(number) || is.na(departure.day) || is.na(departure.month) || is.na(departure.month)) next
  
  url.query <- paste(base, endpoint, carrier, number, "departing", departure.year, departure.month, departure.day, sep = "/")
  url <- paste(url.query, app.info, sep = "?")
  
  result <- GET(url)
  
  # sanity check
  if (result$status_code != 200) next
  
  json <- fromJSON(content(result, "text"), flatten = TRUE)
  data <- as.data.frame(json$scheduledFlights)
  
  if (nrow(data) == 0) next
  
  # append results
  if (is.null(output.data)) {
    output.data <- data
  } else {
    output.data <- bind_rows(output.data, data)
  }
  
}

if (!is.null(output.data)) {
  write.output.records(omni.api, data.frame(output.data), output.number=1)
}
close(omni.api)