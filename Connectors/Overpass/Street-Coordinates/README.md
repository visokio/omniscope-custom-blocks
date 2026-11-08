# Overpass Street Coordinates

For each street name in a field, finds the OpenStreetMap streets with that name through the Overpass API, optionally inside a bounding box, and writes one record per point along each street with its latitude and longitude.

A geocoder gives one point for an address. This block gives the shape of the street itself: every point of the line OpenStreetMap draws for it, in order, so you can draw the street on a map, measure it, or match other points to it. It asks the public [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API), a read-only query service over OpenStreetMap data.

- Each distinct street name in the field is one request. Empty values are skipped.
- **Streets** are OpenStreetMap ways with a `highway` tag (roads, lanes, footpaths and so on). Buildings, rivers or shops whose name contains the street name are not returned.
- **Exact name** (the default) finds ways whose name is exactly the value; OpenStreetMap names are case-sensitive. **Name contains** finds names containing the value in any case, so `High Street` also finds `High Street North`.
- A **bounding box** keeps the search to your town or region. Without one the whole world is searched: slow, liable to time out, and every High Street in the country comes back.
- A long street is often several ways (split at junctions or where its properties change); each way has its own Way ID, and Point numbers the points along each way from 1.
- When the server is busy (HTTP 429 or 504) the block waits 30 seconds and tries again, up to three times, as the server's usage policy asks.

## Language and libraries

Python. It uses requests (Apache License 2.0) for the HTTP calls and pandas (BSD 3-Clause) for the output. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

Map data © OpenStreetMap contributors, available under the Open Database Licence (https://www.openstreetmap.org/copyright). Credit OpenStreetMap where you publish results.

## Inputs

- **Input 1**: records with a text field of street names. Other fields are not passed through: join the output back to the input on the street field.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Street name field | `addressField` | Field | The field that holds the street names. Each distinct name is looked up once. From input 1. |
| Match | `matchMode` | Choice | **Exact name** (`exact`, the default) or **Name contains** (`contains`, any case). |
| Bounding box | `bbox` | Text | South, west, north, east in decimal degrees, such as `53.77, -1.58, 53.83, -1.50`. Empty: the whole world. |
| Overpass API address | `endpoint` | Text | The server to ask. Default `https://overpass-api.de/api/interpreter`, the main public instance. |

## Outputs

- **Points** (`Output Data`): one record per point along each matching street.
  - The street name as given, under the input field's name (with ` (input)` added if the input field is called Street name, Way ID, Point, Node ID, Latitude or Longitude).
  - **Street name**: the name in OpenStreetMap (differs from the input with Name contains).
  - **Way ID** (whole number): the OpenStreetMap way.
  - **Point** (whole number): the point's position along the way, from 1.
  - **Node ID** (whole number): the OpenStreetMap node.
  - **Latitude**, **Longitude** (decimal degrees, WGS 84).

The block's message says how many street names had no match.

## Limits

- The public server is shared: its usage policy asks for no more than about 10,000 requests and 1 GB a day per user, much less for regular automated use. For many street names or frequent runs, use your own Overpass server (Overpass API address).
- Street names are matched as written in OpenStreetMap: abbreviations (`St` for `Street`) and spelling must agree, or use Name contains with the distinctive part.
- Each query may run for up to 120 seconds on the server; a whole-world search for a common name can exceed it, and the block then stops with the server's message.
- Points are in the order OpenStreetMap stores them; the direction of a way says nothing about traffic direction.

## Source

[script.py](script.py)

The tests in `tests/` run the script against an invented Overpass server (`tests/canned/ways.json`, written by `tests/make_canned.py`, which also writes `sample-data/deliveries.csv`); the street geometry in it is invented. `sample-data/placeholder.csv` is the block's output for that data, for trying a workflow without calling the server.

The `Python/` folder holds an older stand-alone version of the script; it is not listed in the block library.
