import json

import pandas as pd
import geopandas as gpd
import shapely.geometry
import shapely.wkt
from omniscope.api import OmniscopeApi


def parse_geometry(value):
    """A shape from GeoJSON geometry (or a Feature) or WKT text; None when empty or not readable."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.startswith("{"):
            obj = json.loads(text)
            if obj.get("type") == "Feature":
                obj = obj.get("geometry")
            return shapely.geometry.shape(obj) if obj else None
        return shapely.wkt.loads(text)
    except Exception:  # noqa: BLE001 - an unreadable shape counts as no shape
        return None


def shapes_from_records(data, geometry_field):
    """Records with a GeoJSON / WKT text field as a GeoDataFrame; coordinates taken as longitude / latitude (WGS 84)."""
    geoms = [parse_geometry(v) for v in data[geometry_field]]
    present = data[geometry_field].notna() & (data[geometry_field].astype(str).str.strip() != "")
    unreadable = sum(1 for g, p in zip(geoms, present) if g is None and p)
    frame = pd.DataFrame(data.drop(columns=[geometry_field])).reset_index(drop=True)
    return gpd.GeoDataFrame(frame, geometry=gpd.GeoSeries(geoms, crs="EPSG:4326")), unreadable

omniscope_api = OmniscopeApi()

shp_file = omniscope_api.get_option("shp_file")
label = omniscope_api.get_option("label")
lat_field = omniscope_api.get_option("latitude_field")
lon_field = omniscope_api.get_option("longitude_field")
region_geometry_field = omniscope_api.get_option("regionGeometryField")
region_label_field = omniscope_api.get_option("regionLabelField")
REGIONS_FIELD = "regions"

region_data = omniscope_api.read_input_records(input_number=1)
unreadable = 0
if region_data is not None and region_geometry_field:
    # Regions as records on the second input: a field of GeoJSON geometry or WKT text
    for f in (region_geometry_field, region_label_field):
        if f and f not in region_data.columns:
            omniscope_api.abort(f"The second input has no field called \"{f}\".")
    if region_label_field == region_geometry_field:
        omniscope_api.abort("The region label field and the geometry field must be different fields.")
    shapes, unreadable = shapes_from_records(region_data, region_geometry_field)
    label = region_label_field
elif shp_file:
    try:
        shapes = gpd.read_file(shp_file)
    except Exception as e:  # noqa: BLE001 - any read failure is reported to the user
        omniscope_api.abort(f"Could not read the regions file \"{shp_file}\": {e}")
elif region_data is not None:
    omniscope_api.abort("Choose the second input's field that holds the shapes (GeoJSON or WKT) in "
                        "\"Region geometry field\".")
else:
    omniscope_api.abort("Connect the regions to the second input and choose the \"Region geometry field\", "
                        "or choose a file in \"Shapefile\".")

if shapes.crs is None:
    # GeoJSON without a "crs" member is longitude / latitude (WGS 84) by definition
    shapes = shapes.set_crs("EPSG:4326")
geom_name = shapes.geometry.name
properties = [c for c in shapes.columns if c != geom_name]

# Second output: the regions' properties and their shapes as text, to see which property to use as the label
regions = pd.DataFrame(shapes[properties]).reset_index(drop=True)
regions["geometry"] = [g.wkt if g is not None else None for g in shapes.geometry]
omniscope_api.write_output_records(regions, output_number=1)
note = f"; {unreadable} geometry values were not GeoJSON or WKT" if unreadable else ""

if not label or not lat_field or not lon_field:
    omniscope_api.close(
        f"{len(shapes)} regions read{note}. Choose the label, latitude and longitude fields to join points to them."
    )
else:
    if label not in properties:
        omniscope_api.abort(
            f"The regions have no property called \"{label}\". Properties: "
            + (", ".join(properties) if properties else "(none)") + "."
        )

    input_data = omniscope_api.read_input_records(input_number=0)
    if input_data is None:
        omniscope_api.abort("Connect the records with latitude and longitude to the block's input.")
    for f in (lat_field, lon_field):
        if f not in input_data.columns:
            omniscope_api.abort(f"The input has no field called \"{f}\".")
        if not pd.api.types.is_numeric_dtype(input_data[f].dtype) or pd.api.types.is_bool_dtype(input_data[f].dtype):
            omniscope_api.abort(f"\"{f}\" must be a number field (decimal degrees).")

    lat = input_data[lat_field].astype("float64").to_numpy()
    lon = input_data[lon_field].astype("float64").to_numpy()
    points = gpd.GeoDataFrame(
        {"_row": range(len(input_data))},
        geometry=gpd.points_from_xy(lon, lat),
        crs="EPSG:4326",
    ).to_crs(shapes.crs)  # the regions' own coordinates (metres for a projected shapefile)

    region_labels = shapes[[label, geom_name]].copy()
    region_labels["_order"] = range(len(region_labels))
    region_labels = region_labels[region_labels[label].notna() & region_labels.geometry.notna()]
    # whole-number codes read as decimals (because one region has none) are written without ".0"
    region_labels[label] = [
        str(int(v)) if isinstance(v, float) and v.is_integer() else str(v) for v in region_labels[label]
    ]

    hits = gpd.sjoin(points, region_labels, how="inner", predicate="within")
    hits = hits.sort_values(["_row", "_order"])
    joined = hits.groupby("_row")[label].agg(",".join)

    output_data = input_data.copy()
    output_data[REGIONS_FIELD] = pd.Series(
        [joined.get(i) for i in range(len(output_data))], index=output_data.index, dtype=object
    )

    inside = int(output_data[REGIONS_FIELD].notna().sum())
    omniscope_api.write_output_records(output_data, output_number=0)
    omniscope_api.close(f"{inside} of {len(output_data)} points are in a region ({len(shapes)} regions){note}.")
