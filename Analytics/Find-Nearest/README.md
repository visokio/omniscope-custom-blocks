# Find Nearest

Finds the k nearest points in a second input for each point in the first, by great-circle distance, with an optional distance limit and a catchment summary per destination.

For each point in the **first input** (customers, properties, incidents, vehicles) finds the **nearest points in the second input** (stores, branches, depots, engineers, competitors) by straight-line (great-circle) distance on the earth's surface.

- **k nearest**: the single nearest, or the nearest 3, 5 or more, each with its rank
- **Maximum distance**: only matches within, say, 25 km; points with nothing in range are kept and marked *None within distance* (or dropped)
- Distance in **kilometres or miles**, plus the **bearing** and compass **direction** from the point to its match
- All fields of the matched destination are appended (prefixed *Nearest:*)
- A second output gives a **catchment summary** per destination: how many points have it as their nearest, mean, median and furthest distance, share of points

Latitude and longitude in decimal degrees (WGS84). Pure numpy: fine for hundreds of thousands of points against thousands of destinations.


## Language
Python

## Inputs
- **Input 1**: points to search from (latitude, longitude).
- **Input 2**: points to find (latitude, longitude).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Points to search from (input 1) | Latitude | `origin_lat` | Field | Latitude of each point in input 1, in decimal degrees. From input 1. |
| Points to search from (input 1) | Longitude | `origin_lon` | Field | Longitude of each point in input 1, in decimal degrees. From input 1. |
| Points to find (input 2) | Latitude | `dest_lat` | Field | Latitude of each candidate in input 2, in decimal degrees. From input 2. |
| Points to find (input 2) | Longitude | `dest_lon` | Field | Longitude of each candidate in input 2, in decimal degrees. From input 2. |
| Points to find (input 2) | Name or ID (for the summary) | `dest_id` | Field | Optional field naming each destination in the catchment summary. From input 2. |
| Search | Number of nearest points | `k` | Whole number | 1 for the nearest only; more gives one row per match, ranked. Default: 1. |
| Search | Maximum distance | `max_distance` | Decimal number | 0 = no limit. Default: 0.0. |
| Search | Distance unit | `unit` | Choice | Unit for distances and the maximum distance. Choices: Kilometres; Miles. Default: Kilometres. |
| Search | Keep points with no match | `keep_unmatched` | Tick box | Keep points with no destination in range (or invalid coordinates), with an empty match. Default: ticked. |

## Outputs
- **Nearest matches** (`nearest`): Input 1 records with the matched destination's fields, Nearest Rank, distance, bearing, direction and match status.
- **Catchment summary** (`catchments`): One row per destination: points nearest to it, mean / median / furthest distance, share of points.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
