import json
import warnings

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

file_path = omniscope_api.get_option("geojsonfile")
id_field = omniscope_api.get_option("shapeIDfield")
point_type = omniscope_api.get_option("pointType") or "centroid"
geometry_field = omniscope_api.get_option("geometryField")
input_id_field = omniscope_api.get_option("inputIdField")

input_data = omniscope_api.read_input_records(input_number=0)
unreadable = 0
if input_data is not None and geometry_field:
    # Shapes as records: a field of GeoJSON geometry or WKT text
    if geometry_field not in input_data.columns:
        omniscope_api.abort(f"The input has no field called \"{geometry_field}\".")
    if input_id_field and input_id_field not in input_data.columns:
        omniscope_api.abort(f"The input has no field called \"{input_id_field}\".")
    if input_id_field == geometry_field:
        omniscope_api.abort("The ID field and the geometry field must be different fields.")
    shapes, unreadable = shapes_from_records(input_data, geometry_field)
    id_field = input_id_field
elif file_path:
    try:
        shapes = gpd.read_file(file_path)
    except Exception as e:  # noqa: BLE001 - any read failure is reported to the user
        omniscope_api.abort(f"Could not read the shapes file \"{file_path}\": {e}")
elif input_data is not None:
    omniscope_api.abort("Choose the input field that holds the shapes (GeoJSON or WKT) in \"Geometry field\".")
else:
    omniscope_api.abort("Connect records with shapes to the input and choose the \"Geometry field\", "
                        "or choose a file in \"Shapes file\".")

properties = [c for c in shapes.columns if c != shapes.geometry.name]

if id_field:
    if id_field not in properties:
        omniscope_api.abort(
            f"The shapes have no property called \"{id_field}\". Properties in the file: "
            + (", ".join(properties) if properties else "(none)") + "."
        )
    keep = [id_field]
else:
    keep = [p for p in properties if p not in ("Lat", "Long")]

geometry = shapes.geometry
if geometry.crs is None:
    # GeoJSON without a "crs" member is longitude / latitude (WGS 84) by definition
    geometry = geometry.set_crs("EPSG:4326")

with warnings.catch_warnings():
    # In a longitude / latitude file the point is worked out on the degrees as flat coordinates (documented).
    warnings.simplefilter("ignore", UserWarning)
    if point_type == "inside":
        points = geometry.representative_point()
    else:
        points = geometry.centroid

# Calculated in the file's own coordinates (metres for a projected file), then given as latitude / longitude
points = points.to_crs("EPSG:4326")

has_point = points.notna() & ~points.is_empty
result = pd.DataFrame(shapes[keep]).reset_index(drop=True)
result["Lat"] = [p.y if ok else None for p, ok in zip(points, has_point)]
result["Long"] = [p.x if ok else None for p, ok in zip(points, has_point)]
result["Lat"] = result["Lat"].astype("float64")
result["Long"] = result["Long"].astype("float64")

missing = int((~has_point).sum())
message = f"{len(result)} shapes" + (f", {missing} without a geometry (empty Lat and Long)" if missing else "")
if unreadable:
    message += f"; {unreadable} geometry values were not GeoJSON or WKT"

omniscope_api.write_output_records(result, output_number=0)
omniscope_api.close(message)
