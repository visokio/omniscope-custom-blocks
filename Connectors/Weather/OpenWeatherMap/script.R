library(omniscope.api)

omni.api = omniscope.api()

input.data = read.input.records(omni.api, input.number=1)

library(httr)
library(jsonlite)
library(data.table)
library(dplyr)


appid <- get.option(omni.api, "appid")
apiChoice <- get.option(omni.api, "apiChoice")
searchChoice <- get.option(omni.api, "searchChoice")
unitsChoice <- get.option(omni.api, "unitsChoice")

latitude.field <- get.option(omni.api, "latitudeField")
longitude.field <- get.option(omni.api, "longitudeField")

city.field <- get.option(omni.api, "cityField")
state.field <- get.option(omni.api, "stateField")
postcode.field <- get.option(omni.api, "postcodeField")
country.field <- get.option(omni.api, "countryField")

apply.rate.limit <- get.option(omni.api, "applyRateLimit")



get.endpoint <- function(apiChoice) {
	base <- "https://api.openweathermap.org"
	if (apiChoice == "CURRENT") {
		endpoint <- "data/2.5/weather"
	} else if (apiChoice == "FORECAST") {
		endpoint <- "data/2.5/forecast"
    } else {
    	cancel(omni.api, "unknown api type")
    }
    
    paste(base, endpoint, sep = "/")
}

get.metric <- function(unitsChoice) {
	if (unitsChoice == "CELSIUS") {
    	return (paste("units", "metric", sep="="))
    } else if (unitsChoice == "FAHRENHEIT") {
    	return (paste("units", "imperial", sep="="))
    } else {
    	return (NULL)
    }
}


get.lat.lon.params <- function(lat, lon) {
  lat.string <- paste("lat", trimws(lat), sep="=")
  lon.string <- paste("lon", trimws(lon), sep="=")
  
  args <- c(lat.string, lon.string)
  
  if (!is.null(units)) {
  	units.sring <- paste("units", units, sep="=")
  	args <- c(args, units.sring)
  }
  
  paste(args, collapse="&")
}

get.city.params <- function(city, state, country) {
  args <- c(trimws(city))
  
  if (!is.null(state)) args <- c(args, trimws(state))

  if (!is.null(country)) args <- c(args, trimws(country))

  args.string <- paste(args, collapse=",")
  
  paste("q", args.string, sep="=")
  
}

get.postcode.params <- function(postcode, country) {
  args <- c(trimws(postcode))
  
  if (!is.null(country)) args <- c(args, trimws(country))

  args.string <- paste(args, collapse=",")
  
  paste("zip", args.string, sep="=")
  
}


url.query <- get.endpoint(apiChoice)
id.string <- paste("appid", appid, sep="=")
units <- get.metric(unitsChoice)



rate.limit <- 1.1
last.query <- NULL
wait.for.rate.limit <-function() {

  if (!apply.rate.limit) return()
  
  duration <- NULL
  if (!is.null(last.query)) {
    duration = as.numeric(difftime(Sys.time(), last.query, units="secs"))
  }
  
  if (is.null(last.query) || duration >= rate.limit) {
    last.query <<- Sys.time()
    return()
  }
  
  Sys.sleep(rate.limit - duration)
  wait.for.rate.limit()
  
}

wait.for.api.cooldown <- function() {
	ten.minutes <- 60 * 10
	Sys.sleep(ten.minutes)
}


get.forecast <- function(row) {

  wait.for.rate.limit()
  
  if (searchChoice == "LATLON") {
    if (is.null(latitude.field) || !(latitude.field %in% names(row))) cancel(omni.api, "Latitude field must be specified")
    if (is.null(longitude.field) || !(longitude.field %in% names(row))) cancel(omni.api, "Longitude field must be specified")
    latitude <- row[latitude.field]
    longitude <- row[longitude.field]
  	search.params <- get.lat.lon.params(latitude, longitude)
  } else if (searchChoice == "CITY") {
  	city <- NULL
  	state <- NULL
  	country <- NULL
    if (is.null(city.field) || !(city.field %in% names(row))) cancel(omni.api, "City field must be specified")
    city <- row[city.field]
    if (!is.null(state.field) && state.field %in% names(row)) state <- row[state.field]
    if (!is.null(country.field) && country.field %in% names(row)) country <- row[country.field]
  	search.params <- get.city.params(city, state, country)
  } else if (searchChoice == "POSTCODE") {
  	postcode <- NULL
  	country <- NULL
    if (is.null(postcode.field) || !(postcode.field %in% names(row))) cancel(omni.api, "Postcode field must be specified")
    postcode <- row[postcode.field]
    if (!is.null(country.field) && country.field %in% names(row)) country <- row[country.field]
  	search.params <- get.postcode.params(postcode, country)
  } else {
    cancel(omni.api, "Unknown search type") 
  }

  args <- c(search.params)
  if (!is.null(units)) args <- c(args, units)
  args <- c(args, id.string)
  
  app.params <- paste(args, collapse="&")
  
    
  url <- paste(url.query, app.params, sep = "?")
  
  
    
  result <- GET(url)
  
  #print(paste(name, lat, lon, appid, result$status_code, " "))
  

  # rate limit check
  if (result$status_code == 429) {
  	wait.for.api.cooldown()
    result <- GET(url)
  }
  
  # sanity check
  if (result$status_code != 200) return()

  
  json <- fromJSON(content(result, "text"), flatten = TRUE)
  
  if (apiChoice == "FORECAST") {
    data <- as.data.frame(json$list)
    setDT(data)
    desc <- bind_rows(data$weather)
    data[, weather:=NULL]
    data <- bind_cols(data, desc)
    data$dt_txt <- as.POSIXct(data$dt_txt)
  } else if (apiChoice == "CURRENT") {
    data <- as.data.frame(json)
    setDT(data)
    data[, cod:=NULL]
  } else {
    cancel(omni.api, "Unknown api type")
  }
  
  if (searchChoice == "LATLON") {
    data$latitude <- latitude
    data$longitude <- longitude
  } else if (searchChoice == "CITY") {
    data$city <- city
    if (!is.null(state)) data$state <- state
    if (!is.null(country)) data$country <- country
  } else if (searchChoice == "POSTCODE") {
  	data$postcode <- postcode
    if (!is.null(country)) data$country <- country
  } else {
    cancel(omni.api, "Unknown search type") 
  }
  
  data
}



weather.row <- function(row, name.field, lat.field, lon.field, appid) {
  get.forecast(row[name.field], row[lat.field], row[lon.field], appid)
}

output.data <- bind_rows(apply(input.data, 1, get.forecast))

if (!is.null(output.data)) {
  write.output.records(omni.api, output.data, output.number=1)
}
close(omni.api)