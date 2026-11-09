# OpenWeatherMap

Adds the current weather, or a 5-day forecast in 3-hour steps, from [OpenWeatherMap](https://openweathermap.org/) to each location in the input, found by latitude and longitude, city or postcode.

Sites, stores, customers or events often have a location but no weather. This block calls OpenWeatherMap once for each distinct location in the input and writes the answer as records, with the input's location fields and an identifying field beside them so the weather can be joined back.

- **Current weather**: one record per location, with temperature, feels-like, humidity, pressure, wind, cloud cover, rain and snow in the last hour, visibility, the weather condition, and sunrise and sunset.
- **5-day forecast**: 40 records per location, one every 3 hours, with the same measures plus the probability of precipitation (`pop`) and rain and snow over the 3 hours.
- Every record has the same fields whatever the weather: rain, snow and gusts are empty when OpenWeatherMap reports none.
- Times (`dt`, `dt_txt`, `sys.sunrise`, `sys.sunset`) are date-times in UTC.

You need an OpenWeatherMap API key: sign up at https://home.openweathermap.org/users/sign_up; the key is under *API keys*. The free plan includes both endpoints this block uses.

## Language and libraries

R. It uses httr (MIT licence) for the calls, jsonlite (MIT) to read the answers and data.table (MPL-2.0) to stack the records. Install them on the Omniscope server's R if they are missing (`install.packages(c("httr", "jsonlite", "data.table"))`).

## Inputs

- **Input 1**: one record per location, with either a latitude and a longitude field (numbers, decimal degrees), a city field (optionally a state and a country code field), or a postcode field (and a country code field).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Authentication | API key | `appid` | Password | Your OpenWeatherMap API key. |
| Authentication | Apply free account rate limit | `applyRateLimit` | Yes/no | Waits 1.1 seconds between calls so a free account stays under 60 calls a minute. Default: ticked. |
| Query | Weather | `apiChoice` | Choice | Current weather (`CURRENT`, default) or 5-day forecast (`FORECAST`). |
| Query | Find locations by | `searchChoice` | Choice | Latitude and longitude (`LATLON`, default), City, state and country code (`CITY`), or Postcode and country code (`POSTCODE`). |
| Query | Units | `unitsChoice` | Choice | Celsius (`CELSIUS`, default; wind in metres a second), Fahrenheit (`FAHRENHEIT`; wind in miles an hour) or Kelvin (`KELVIN`). |
| Query | Field to identify records | `indexField` | Field | Optional. Copied into each output record as `index`. |
| Location fields | Latitude field | `latitudeField` | Field | Latitude, for a latitude and longitude search. Text holding numbers is converted. |
| Location fields | Longitude field | `longitudeField` | Field | Longitude, for a latitude and longitude search. |
| Location fields | City field | `cityField` | Field | City name, for a city search. |
| Location fields | State field | `stateField` | Field | Optional US state code; OpenWeatherMap uses states for the United States only. |
| Location fields | Postcode field | `postcodeField` | Field | Postcode or zip code, for a postcode search. |
| Location fields | Country code field (ISO 3166) | `countryField` | Field | Optional two-letter country code such as `GB`, for city and postcode searches. Without one, a postcode is looked up in the United States. |

## Outputs

- **Weather** (`Output Data`). Current weather: `coord.lon`, `coord.lat`, `weather.id`, `weather.main`, `weather.description`, `weather.icon`, `base`, `main.temp`, `main.feels_like`, `main.temp_min`, `main.temp_max`, `main.pressure`, `main.humidity`, `main.sea_level`, `main.grnd_level`, `visibility`, `wind.speed`, `wind.deg`, `wind.gust`, `clouds.all`, `rain.1h`, `snow.1h`, `dt`, `sys.type`, `sys.id`, `sys.country`, `sys.sunrise`, `sys.sunset`, `timezone` (seconds from UTC), `id`, `name`. Forecast: `dt`, `visibility`, `pop`, `dt_txt`, `main.*` (with `main.temp_kf`), `clouds.all`, `wind.speed`, `wind.deg`, `wind.gust`, `sys.pod` (d or n), `snow.3h`, `rain.3h`, `id`, `main`, `description`, `icon` (the weather condition). Then the input's location fields (`latitude` and `longitude`; or `city`, `state`, `country`; or `postcode`, `country`) and `index`.

The field names are OpenWeatherMap's; its documentation describes each one (https://openweathermap.org/current and https://openweathermap.org/forecast5). When OpenWeatherMap reports more than one weather condition, the first (the primary one) is used.

## Limits

- **City and postcode searches** use OpenWeatherMap's built-in geocoder, which it has marked as deprecated (still answered, no longer maintained). Latitude and longitude is the supported way; the core Geocode block, or OpenWeatherMap's own Geocoding API, can turn addresses into coordinates first.
- A city name can match several places; OpenWeatherMap picks one. Add a country code, and check `name`, `coord.lat` and `coord.lon` in the output.
- Records with no location are skipped; locations OpenWeatherMap cannot find, and calls that fail, are left out. The block's message gives the counts.
- **Calls**: one per distinct location per run. With the rate limit on, 600 locations take about 11 minutes. If OpenWeatherMap answers that the call limit is exceeded (429), the block waits a minute and tries again, up to three times, then stops.
- A refused API key stops the block with OpenWeatherMap's message. A new key can take a little while to become active.
- The forecast is the free 5-day, 3-hour forecast; hourly and daily forecasts are separate OpenWeatherMap products.

## Source

[script.R](script.R)

The tests in `tests/` run the script against invented OpenWeatherMap answers (`tests/canned/`, written by `tests/make_canned.R`), with no live calls. `sample-data/sites.csv` is an invented list of sites; `sample-data/placeholder.csv` is the block's current-weather output for them, for trying a workflow without an API key.
