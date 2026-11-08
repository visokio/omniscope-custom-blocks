# Point-to-Point Distance

Great-circle distance, bearing, direction and midpoint between two latitude / longitude pairs per row, with optional road distance and travel time estimates.

For each row, the **great-circle distance** between two locations (from and to latitude / longitude): journeys, deliveries, patient travel, customer to store.

- Distance in kilometres or miles (haversine on a spherical Earth, accurate to about 0.5% for most purposes)
- Initial **compass bearing** and direction (N, NE, E...), and the **midpoint**
- Optional **estimated road distance** (straight line times a factor, for example 1.3) and **travel time** at an average speed
- Rows with missing or impossible coordinates are kept and marked

Find Nearest finds the nearest locations from another table; Trade Area Summary counts points around sites. This block measures one pair per row.

## Language
Python

## Inputs
- **Input**: data with from and to latitude and longitude.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | From latitude | `from_lat` | Field | Latitude of the starting point, in decimal degrees. From input 1. |
|  | From longitude | `from_lon` | Field | Longitude of the starting point, in decimal degrees. From input 1. |
|  | To latitude | `to_lat` | Field | Latitude of the destination, in decimal degrees. From input 1. |
|  | To longitude | `to_lon` | Field | Longitude of the destination, in decimal degrees. From input 1. |
|  | Unit | `unit` | Choice | Unit for distances; speed is then km/h or mph. Choices: Kilometres; Miles. Default: Kilometres. |
|  | Road distance factor (optional) | `road_factor` | Decimal number | For example 1.3; 0 = none. Default: 0.0. |
|  | Average speed for travel time (optional) | `speed` | Decimal number | In km/h or mph; needs a road factor. Default: 0.0. |

## Outputs
- **Distances** (`distances`): The input with distance, bearing, direction, midpoint, optional road distance and minutes, valid flag.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
