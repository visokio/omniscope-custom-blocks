# Point in Polygon

Finds which polygon (territory, zone, area) each latitude / longitude point falls in, from GeoJSON or WKT shapes, and counts points per polygon.

Tags each point (customer, property, incident, vehicle position) with the **area it falls in**: sales territory, delivery zone, council or ward, flood zone, catchment. The areas are polygons, one per row of the second input, with the shape in a text field:

- **GeoJSON** geometry (`Polygon`, `MultiPolygon`, or a `Feature`), as exported by most GIS tools and open-data portals
- **WKT** (`POLYGON ((lon lat, ...))`, `MULTIPOLYGON`), as stored in many databases

Holes are respected (a region *outside* a city, for example), and points on overlapping polygons can return the first match or all matches. Every polygon's other fields are appended to its points (prefixed *Polygon:*), and the second output counts the points (and sums a value) per polygon, with a note for any geometry that could not be read.

Coordinates are longitude / latitude in decimal degrees (WGS84). Pure numpy: no GIS libraries to install.

## Language
Python

## Inputs
- **Input 1**: points with latitude and longitude.
- **Input 2**: polygons, one per row, with a GeoJSON or WKT geometry field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Points (input 1) | Latitude | `lat_field` | Field | Latitude of each point, in decimal degrees. From input 1. |
| Points (input 1) | Longitude | `lon_field` | Field | Longitude of each point, in decimal degrees. From input 1. |
| Points (input 1) | Value to sum per polygon (optional) | `value_field` | Field | A number to total per polygon, such as spend. From input 1. |
| Polygons (input 2) | Geometry (GeoJSON or WKT) | `geometry_field` | Field | The shape of each polygon in input 2, as GeoJSON or WKT text. From input 2. |
| Matching | Points in overlapping polygons | `match_mode` | Choice | Where polygons overlap: keep only the first match, or a row for each. Choices: First matching polygon; One row per matching polygon. Default: First matching polygon. |
| Matching | Keep points outside all polygons | `keep_unmatched` | Tick box | Default: ticked. |

## Outputs
- **Points with polygon** (`points`): Input 1 with the containing polygon's fields, Polygon Row, Polygons Containing Point and Match Status.
- **Polygon summary** (`polygons`): Input 2 (without geometry) with the number of points (and value) in each polygon and a geometry status.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the Shapefile block

The community **Shapefile** block also joins latitude / longitude points to regions, read from a shapefile, a GeoJSON file or shapes on a second input. Use it to read a shapefile directly. Use this block when you also want a count of points per polygon, or every polygon a point falls in where regions overlap.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
