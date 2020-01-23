library(omniscope.api)

omni.api = omniscope.api()

### Parameters

flightstats.app.id <- get.option(omni.api, "appID")

flightstats.app.key <- get.option(omni.api, "appKey")

### Script


library(httr)
library(jsonlite)

# sanity checks
if (is.null(input.data)) stop("No input data")

app.id.string <- paste("appId", flightstats.app.id, sep="=")
app.key.string <- paste("appKey", flightstats.app.key, sep="=")

app.info <- paste(app.id.string, app.key.string, sep="&")

base <- "https://api.flightstats.com"
endpoint <- "flex/airlines/rest/v1/json/active"

url.query <- paste(base, endpoint, sep = "/")
url <- paste(url.query, app.info, sep = "?")

result <- GET(url)

json <- fromJSON(content(result, "text"), flatten = TRUE)

output.data <- as.data.frame(json$airlines)

if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)