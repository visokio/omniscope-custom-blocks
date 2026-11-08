# Centroids from GeoJSON

Finds a centre point (latitude and longitude) for each shape, from records with GeoJSON or WKT shapes or from a GeoJSON file or shapefile, and outputs it with the shape's ID or other fields.

Boundary files describe regions as shapes. Many views and blocks work with points: a map pin or label per region, a distance from a region to a site, a join to point data. This block gives one record per shape with a **Lat** and **Long** for its centre.

Where the shapes come from:

- **Records on the input** (used when a **Geometry field** is chosen): one record per shape, with a text field holding the shape as GeoJSON geometry (`{"type": "Polygon", "coordinates": ...}`, or a whole GeoJSON Feature) or as WKT (`POLYGON ((-1.6 53.12, ...))`). Each value is recognised as one or the other, so a field can mix them. The coordinates are taken as longitude / latitude in degrees (WGS 84), the usual form for both. Choose an **ID field** to keep beside Lat and Long, or leave it empty to keep every other field. This works with data from any source (a database table of boundaries, a CSV, a File block) and travels with the project.
- **A shapes file** (used when no geometry field is chosen): a GeoJSON file, a shapefile or a GeoPackage, by its path on the server, with an optional **Shape ID property**. Files in a projected coordinate system are converted (below).

How the point is found:

- **Centroid** (the default): the centre of the shape's area. For a C- or L-shaped region it can fall outside the shape, and for a region in several pieces (a mainland and an island) it lies between them, weighted by area.
- **Point inside the shape**: a point that is always within the shape, near its middle (Shapely's representative point). Use it for labels and pins that must sit on the region.
- **Coordinates of a file**: a file in a projected coordinate system (in metres, such as British National Grid, common in shapefiles) is handled: the point is found in the file's own coordinates and then converted to latitude and longitude (WGS 84). In a longitude / latitude file the centroid is worked out on the degrees as flat coordinates, which for large shapes far from the equator is not exactly the centre measured on the ground. A GeoJSON file that does not state a coordinate system is taken as longitude / latitude, as the GeoJSON standard says.

Things to know:

- **Shape ID property** (for a file) is case-sensitive. Leave it empty to output every property of the shapes; if the name is not found, the block stops and lists the properties the file has.
- A shape with no geometry, or with a geometry value that is neither GeoJSON nor WKT, stays in the output with an empty Lat and Long; the block's message says how many.
- If the shapes already have fields or properties called `Lat` or `Long`, they are replaced by the centre point.

## Language and libraries

Python, using geopandas (BSD 3-Clause) with the packages it installs: Shapely (BSD 3-Clause) for the geometry and for reading WKT and GeoJSON text, pyproj (MIT) for the coordinate conversion and pyogrio (MIT) to read the file; and pandas (BSD 3-Clause), part of Omniscope's Python environment. The manifest lists `geopandas` as a dependency, so Omniscope installs it with pip on first run if it is missing; the server needs access to the Python package index for that, or geopandas installed beforehand.

## Inputs
- **Input 1** (optional): one record per shape, with a text field of GeoJSON geometry or WKT. Not needed when the shapes come from a file.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Geometry field | `geometryField` | Field | The input field holding each shape as GeoJSON geometry or WKT text (longitude / latitude, WGS 84). When chosen, the input is used and the file is not. From input 1. |
| ID field | `inputIdField` | Field | Optional: the input field to keep beside Lat and Long; empty keeps every field except the geometry. From input 1. |
| Shapes file | `geojsonfile` | File | Used when no geometry field is chosen: a GeoJSON file (.geojson, .json), a shapefile (.shp, with its .shx, .dbf and .prj files beside it, or a .zip of them) or a GeoPackage (.gpkg). |
| Shape ID property | `shapeIDfield` | Text | For a file: the property that identifies each shape, for example `code` or `name` (case matters). Leave empty to output every property. |
| Point | `pointType` | Choice | Centroid (`centroid`, default) or Point inside the shape (`inside`). |

## Outputs
- **Centroids** (`Output Data`): one record per shape, in the input's or file's order: the ID field or Shape ID property (or every other field or property), then **Lat** and **Long** (Decimal, degrees, WGS 84).

## Size of input

20,000 small square shapes in a GeoJSON file (about 4 MB) took under a second in tests.

## Source
[script.py](script.py)

The sample data in `sample-data/` (`districts.csv`, with the shapes as WKT text, and the same shapes in `districts.geojson`, both made by `make-districts.py`) is four invented districts with made-up names and shapes, not real boundaries.
