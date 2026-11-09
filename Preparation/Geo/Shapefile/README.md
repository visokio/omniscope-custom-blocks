# Shapefile

Finds which region each latitude / longitude point falls in, and adds the region's label to the point's record. The regions come from records with GeoJSON or WKT shapes on a second input, or from a shapefile or GeoJSON file.

Points (customers, depots, incidents) are easy to come by; the region each one belongs to (sales territory, district, catchment) usually is not. The regions come as shapes: a boundary file, or a table with each region's shape as GeoJSON or WKT text. This block reads them, tests every point against every region, and adds a **regions** field with the label of the region each point is in.

Where the regions come from (one of the two):

- **Records on the second input** (used when connected and a **Region geometry field** is chosen): one record per region, with a text field holding its shape as GeoJSON geometry (`{"type": "Polygon", ...}`, or a whole Feature) or as WKT (`POLYGON ((...))`); each value is recognised as one or the other. Choose the field to use as the label in **Region label field**. The coordinates are taken as longitude / latitude in degrees (WGS 84). The regions can come from any source (a database table, a CSV, a File block) and travel with the project.
- **A file** (used otherwise), by its path on the server, as below.

With a file:

- **The file**: a shapefile (`.shp` with its `.shx`, `.dbf` and `.prj` files beside it, or all of them in one `.zip`), a GeoJSON file or a GeoPackage.
- **First run**: with only the file chosen, the block writes the **Regions** output: one record per region with its properties and its shape as text (WKT). Look there for the property that names the regions, such as a name or a code, and enter it as the **Label property**.
- **Second run**: with the label property and the first input's **Latitude** and **Longitude** fields chosen, the **Joined** output is the input records with a **regions** field.
- **Coordinates**: the points (on the first input) are always taken as longitude / latitude in decimal degrees (WGS 84). If the regions file is in a projected coordinate system (in metres, such as British National Grid, common in UK shapefiles), the points are converted to it before matching. A GeoJSON file that does not state a coordinate system is taken as longitude / latitude, as the GeoJSON standard says.

Things to know:

- A point inside **two overlapping regions** gets both labels, separated by commas, in the order of the regions (records or file).
- A point in **no region**, exactly **on a region's edge**, or with an empty latitude or longitude gets an empty **regions** value. The block's message says how many points were placed.
- A region with no label value, or with a geometry value that is neither GeoJSON nor WKT, is skipped (the block's message counts unreadable shapes). Whole-number labels are written without decimals (`7`, not `7.0`).
- The **Label property** (for a file) is case-sensitive; if it is not found, the block stops and lists the properties the file has.
- An existing input field called `regions` is replaced.
- The WKT in the Regions output is in the file's own coordinates (metres for a projected file).

## Language and libraries

Python, using geopandas (BSD 3-Clause) with the packages it installs: Shapely (BSD 3-Clause) for reading GeoJSON and WKT text and the point-in-region tests, pyproj (MIT) for the coordinate conversion and pyogrio (MIT) to read the file; and pandas (BSD 3-Clause), part of Omniscope's Python environment. The manifest lists `geopandas` as a dependency, so Omniscope installs it with pip on first run if it is missing; the server needs access to the Python package index for that, or geopandas installed beforehand. Earlier versions also imported `fiona`, which recent geopandas no longer installs; it is no longer needed.

## Inputs
- **Input 1**: points, with latitude and longitude fields in decimal degrees. Only needed for the Joined output.
- **Input 2** (optional): the regions, one record per region, with a text field of GeoJSON geometry or WKT. Not needed when the regions come from a file.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Points | Latitude | `latitude_field` | Field | The input field with each point's latitude, in decimal degrees. From input 1. |
| Points | Longitude | `longitude_field` | Field | The input field with each point's longitude, in decimal degrees. From input 1. |
| Regions from the second input | Region geometry field | `regionGeometryField` | Field | The field holding each region's shape as GeoJSON geometry or WKT text (longitude / latitude, WGS 84). When chosen (and input 2 connected), the file is not used. From input 2. |
| Regions from the second input | Region label field | `regionLabelField` | Field | The field to put in the regions field, for example a name or code. From input 2. |
| Or: regions from a file | Shapefile | `shp_file` | File | Used when the second input is not: a path on the server to a shapefile (.shp, with its .shx, .dbf and .prj, or a .zip of them), a GeoJSON file or a GeoPackage. |
| Or: regions from a file | Label property | `label` | Text | The property of the regions to put in the regions field, for example a name or code. |

## Outputs
- **Joined** (`Output Data`): the input records, in their order, with a **regions** field (Text). Written only when the label (field or property) and both point fields are chosen.
- **Regions** (`Output Data 2`): one record per region: its other fields (or the file's properties) and a **geometry** field with its shape as WKT text.

## Size of input

The points are matched with a spatial index. 100,000 points against 2,500 square regions took about 2 seconds in tests. Large, detailed boundary files take longer to read, and the WKT in the Regions output can be very long for detailed shapes.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented: `districts.csv` (shapes as WKT text) and `districts.geojson` (the same shapes), both made by `make-districts.py`, are four made-up districts, not real boundaries, and `depots.csv` is 12 made-up depots.
