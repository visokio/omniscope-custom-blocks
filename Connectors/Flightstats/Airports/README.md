# FlightStats Airports

Loads the list of airports from the FlightStats (Cirium Flex) API: one record per airport, with its codes, name, city, country, time zone, position and elevation. Use it as a lookup table, for example to put the departure and arrival airports of a list of flights on a map.

**Service status.** FlightStats (Cirium) has said that its legacy Flex APIs, which this block calls, will keep working until 31 December 2026, and that new integrations should use its newer Cirium Sky API, which this block does not call. Free trials are now offered only for the newer API, so a new user may not be able to get Flex credentials. Check the provider's current terms before building on this block.

## Language and libraries

R, with the httr and jsonlite packages (both MIT licence). Install them on the Omniscope server's R if they are missing (`install.packages(c("httr", "jsonlite"))`).

## Inputs

None. The block reads from FlightStats.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Credentials | App ID | `appID` | Text | The application ID of your FlightStats (Cirium Flex) account. |
| Credentials | App key | `appKey` | Password | The application key. It is sent in the address of each request, as FlightStats' Flex API expects, so it can appear in the logs of a proxy that inspects HTTPS traffic; it is never written to the output. |
| List | Include inactive airports | `includeInactive` | Yes/no | Also load airports that are no longer active (the API's full list rather than the active list). Default: no. |

## Outputs

- **Airports** (`Output Data`): one record per airport. These fields are always present, in this order, and empty where FlightStats has no value (any further fields it adds follow them):

| Field | What it holds |
|---|---|
| `fs`, `iata`, `icao`, `faa` | FlightStats, IATA, ICAO and FAA codes |
| `name` | Airport name |
| `street1`, `street2`, `city`, `cityCode`, `stateCode`, `postalCode` | Address and city code |
| `countryCode`, `countryName`, `regionName` | Country (ISO code and name) and world region |
| `timeZoneRegionName`, `utcOffsetHours` | Time zone (such as `Europe/London`) and its current offset from UTC |
| `weatherZone` | Weather zone code (US airports) |
| `localTime` | The airport's local time when the list was made, as a date and time (no time zone attached) |
| `latitude`, `longitude`, `elevationFeet` | Position and elevation |
| `classification` | FlightStats' size class, 1 (largest) to 5 |
| `active` | true for an airport that is currently active |
| `delayIndexUrl`, `weatherUrl` | Links to FlightStats' delay and weather services for the airport |

## Limits

- One request per run; the whole list comes back at once.
- Refused credentials, or any other error from FlightStats, stop the block with FlightStats' message.
- The block does not call the newer Cirium Sky API (see Service status above).

## Source

[script.R](script.R). The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` and the answers in `tests/canned/` are invented: the airports are fictional.
