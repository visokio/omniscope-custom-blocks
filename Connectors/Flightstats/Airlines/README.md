# FlightStats Airlines

Loads the list of airlines from the FlightStats (Cirium Flex) API: one record per airline, with its codes, name, phone number and whether it is active. Use it as a lookup table, for example to turn the carrier codes in a list of flights or bookings into airline names.

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
| List | Include inactive airlines | `includeInactive` | Yes/no | Also load airlines that no longer operate (the API's full list rather than the active list). Default: no. |

## Outputs

- **Airlines** (`Output Data`): one record per airline, with these fields, always present and in this order (any further fields FlightStats adds follow them):

| Field | What it holds |
|---|---|
| `fs` | The FlightStats code: usually the IATA code; codes with an asterisk (such as `WY*`) are FlightStats' own, for airlines without one |
| `iata` | IATA code (empty if the airline has none) |
| `icao` | ICAO code |
| `name` | Airline name |
| `phoneNumber` | Phone number, where FlightStats has one |
| `active` | true for an airline that currently operates |

## Limits

- One request per run; the whole list comes back at once.
- Refused credentials, or any other error from FlightStats, stop the block with FlightStats' message.
- The block does not call the newer Cirium Sky API (see Service status above).

## Source

[script.R](script.R). The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` and the answers in `tests/canned/` are invented: the airlines are fictional.
