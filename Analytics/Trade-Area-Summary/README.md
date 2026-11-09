# Trade Area Summary

Counts and sums points within several radii of each site, with exclusive and shared catchment, and the nearest site and distance band per point.

For each **site** (store, branch, depot, clinic, school), how many **points** (customers, households, competitors, incidents) lie within each of several **radii**, what value they carry, and how much of that is **shared with other sites**.

- Great-circle (haversine) distances in kilometres or miles, from latitude and longitude
- Per site and radius: points and value within, share of all points and value, **exclusive** points (no other site within the same radius), shared points, average distance
- Per point: **nearest site** and distance, a **distance band** (0-1 km, 1-3 km...), and how many sites reach it within the largest radius

Connect the sites to input 1 and the points to input 2. Rows without valid coordinates are kept and marked. Find Nearest gives the k nearest sites per point; this block summarises catchments by radius.

## Language
Python

## Inputs
- **Input 1**: sites with latitude and longitude.
- **Input 2**: points (customers, households) with latitude and longitude.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Sites (input 1) | Site name | `site_field` | Field | Names each site, such as a store or branch. From input 1. |
| Sites (input 1) | Latitude | `site_lat` | Field | Latitude of each site, in decimal degrees. From input 1. |
| Sites (input 1) | Longitude | `site_lon` | Field | Longitude of each site, in decimal degrees. From input 1. |
| Points (input 2) | Latitude | `point_lat` | Field | Latitude of each point in input 2, in decimal degrees. From input 2. |
| Points (input 2) | Longitude | `point_lon` | Field | Longitude of each point in input 2, in decimal degrees. From input 2. |
| Points (input 2) | Value (optional) | `point_value` | Field | For example annual spend or households. From input 2. |
| Points (input 2) | Point ID (optional) | `point_id` | Field | Identifies each point in the per-point output. From input 2. |
| Radii | Radii | `radii` | Text | Comma-separated, for example: 1, 3, 5, 10 Default: 1, 3, 5, 10. |
| Radii | Unit | `unit` | Choice | Unit for the radii and distances. Choices: Kilometres; Miles. Default: Kilometres. |

## Outputs
- **Sites** (`sites`): Per site and radius: points and value within, shares, exclusive and shared points, average distance.
- **Points** (`points`): The points with nearest site, distance, distance band and number of sites within the largest radius.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
