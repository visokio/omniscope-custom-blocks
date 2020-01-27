# Flightstats Flights

Requests information about flights specified in the input data from flightstats (https://www.flightstats.com). If the flight exists the result will contain live information, otherwise it will not be part of it. The script needs your flightstats app id and key which needs to be obtained either through buying their service or signing up for a test account.

## Language
R

## Input fields
### flight.carrier.field
The carrier part of the fight number, i.e. the "LH" in LH1234
### flight.number.field
The number part of the fight number, i.e. the "1234" in LH1234
### flight.date.field
The date the flight is scheduled

## Parameters
### flightstats.app.id
The app id as provided by flightstats.
### flightstats.app.key
The app key as provided by flightstats.

## Dependencies
httr, jsonlite, data.table, dplyr, lubridate

## Source
[script.R](https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Flightstats/Flights/R/script.R)
