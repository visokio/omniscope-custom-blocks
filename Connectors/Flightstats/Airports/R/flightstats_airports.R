### Parameters

flightstats.app.id <- "your flightstats app id"

flightstats.app.key <- "your flightstats app key"

### Script


library(httr)
library(jsonlite)


app.id.string <- paste("appId", flightstats.app.id, sep="=")
app.key.string <- paste("appKey", flightstats.app.key, sep="=")

app.info <- paste(app.id.string, app.key.string, sep="&")

base <- "https://api.flightstats.com"
endpoint <- "flex/airports/rest/v1/json/active"

url.query <- paste(base, endpoint, sep = "/")
url <- paste(url.query, app.info, sep = "?")

result <- GET(url)

json <- fromJSON(content(result, "text"), flatten = TRUE)

output.data <- as.data.frame(json$airports)