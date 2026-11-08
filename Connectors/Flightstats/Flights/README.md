# FlightStats Flights

Looks up flights in the FlightStats (Cirium Flex) schedules. Each input record names a flight by carrier code, flight number and departure date ("LH", "1234", 18 November); the output has one record per scheduled leg of that flight, with its departure and arrival airports, local departure and arrival times, terminals, aircraft type and codeshares. Use it to complete a list of bookings or trips that has only flight numbers.

These are **scheduled** times, not live flight status: a delay or cancellation does not show.

**Service status.** FlightStats (Cirium) has said that its legacy Flex APIs, which this block calls, will keep working until 31 December 2026, and that new integrations should use its newer Cirium Sky API, which this block does not call. Free trials are now offered only for the newer API, so a new user may not be able to get Flex credentials. Check the provider's current terms before building on this block.

## Language and libraries

R, with the httr and jsonlite packages (both MIT licence). Install them on the Omniscope server's R if they are missing (`install.packages(c("httr", "jsonlite"))`).

## Inputs

- **Input 1**: the flights to look up, with a carrier field (text), a flight number field (text or whole number) and a departure date field (date).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Credentials | App ID | `appID` | Text | The application ID of your FlightStats (Cirium Flex) account. |
| Credentials | App key | `appKey` | Password | The application key. It is sent in the address of each request, as FlightStats' Flex API expects, so it can appear in the logs of a proxy that inspects HTTPS traffic; it is never written to the output. |
| Flights to look up | Carrier field | `carrierField` | Field | Text field with the airline code: the "LH" in LH1234 (FlightStats, IATA or ICAO code; case does not matter). |
| Flights to look up | Flight number field | `flightNumberField` | Field | The number part: the "1234" in LH1234, up to 4 digits. |
| Flights to look up | Departure date field | `dateField` | Field | Date field with the day the flight departs. The date in UTC is used; a time of day is ignored. |

## Outputs

- **Flights** (`Output Data`): one record per scheduled leg (a flight number that stops on the way has a record for each leg). Fields, always in this order:

| Field | What it holds |
|---|---|
| `Requested carrier`, `Requested flight number`, `Requested date` | The flight as asked for, to join the result back to the input |
| `carrierFsCode`, `flightNumber` | The operating flight, as FlightStats names it |
| `departureAirportFsCode`, `arrivalAirportFsCode` | Airport codes (FlightStats codes; join to the FlightStats Airports block for names and positions) |
| `departureTime`, `arrivalTime` | Scheduled times, in the **local time of each airport**, as dates and times with no time zone attached |
| `stops` | Number of stops |
| `departureTerminal`, `arrivalTerminal` | Terminals, where known |
| `flightEquipmentIataCode` | Scheduled aircraft type (IATA code) |
| `isCodeshare`, `isWetlease` | true for a codeshare (marketed) flight or a wet-leased one |
| `serviceType`, `serviceClasses`, `trafficRestrictions` | Service type and codes; lists are joined with commas ("Y, J") |
| `codeshares` | The other flight numbers this flight is sold under, joined with commas ("XK1402, OY7402") |
| `referenceCode` | FlightStats' reference for the schedule record |

## How requests are made

- One request per distinct carrier, flight number and day: two bookings on the same flight make one request.
- Records with no carrier, no date, or a flight number that is not 1 to 4 digits are skipped.
- A flight not in the schedules for that day is left out.
- The block's message gives the counts: flights found, distinct requests, not found, skipped and failed.

## Limits

- Refused credentials stop the block with FlightStats' message. Any other failed request is listed in the block's message (the first three) and the rest still come out.
- Requests are made one after another, so a long list takes a while; your FlightStats plan may also limit or charge for the number of requests.
- The block does not call the newer Cirium Sky API (see Service status above).

## Source

[script.R](script.R). The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` and the answers in `tests/canned/` are invented: the airlines, airports and flights are fictional.
