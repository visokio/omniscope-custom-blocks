import json
import os
import time
import zipfile

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "districts.geojson")


def run(path, **options):
    return run_block(HERE, [], {"geojsonfile": path, **options})


def districts_for_shapefile():
    """The sample districts, renamed for a shapefile (which cuts property names to 10 characters)."""
    shapes = gpd.read_file(SAMPLE).rename(columns={"district_code": "code", "district_name": "name"})
    return shapes


def write_geojson(tmp_path, features, name="shapes.geojson"):
    path = tmp_path / name
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return str(path)


def test_sample_centroids_with_id():
    out = run(SAMPLE, shapeIDfield="district_code").raise_for_error().output(0)
    assert list(out.columns) == ["district_code", "Lat", "Long"]
    assert list(out["district_code"]) == ["D01", "D02", "D03", "D04"]
    got = {r.district_code: (r.Lat, r.Long) for r in out.itertuples()}
    assert got["D03"] == pytest.approx((53.06, -1.475))  # a rectangle: its centre
    assert got["D02"] == pytest.approx((53.1625, -1.27375))  # the L-shaped district: centroid in the notch, outside it
    assert str(out["Lat"].dtype) == "float64"


def test_no_id_property_outputs_every_property():
    out = run(SAMPLE).raise_for_error().output(0)
    assert list(out.columns) == ["district_code", "district_name", "households", "Lat", "Long"]
    assert list(out["households"]) == [4200, 2900, 3600, 1800]


def test_point_inside_the_shape_is_within_it():
    shapes = gpd.read_file(SAMPLE)
    centroid = run(SAMPLE, shapeIDfield="district_name").raise_for_error().output(0)
    inside = run(SAMPLE, shapeIDfield="district_name", pointType="inside").raise_for_error().output(0)
    for i, geom in enumerate(shapes.geometry):
        assert geom.contains(Point(inside["Long"][i], inside["Lat"][i]))
    # the L-shaped district's centroid is outside it; the other three are inside
    flags = [geom.contains(Point(centroid["Long"][i], centroid["Lat"][i])) for i, geom in enumerate(shapes.geometry)]
    assert flags == [True, False, True, True]


def test_projected_file_gives_latitude_and_longitude(tmp_path):
    # the same districts in British National Grid (metres): the output must still be degrees
    path = str(tmp_path / "districts-bng.shp")
    districts_for_shapefile().to_crs("EPSG:27700").to_file(path)
    out = run(path, shapeIDfield="code").raise_for_error().output(0)
    expected = run(SAMPLE, shapeIDfield="district_code").raise_for_error().output(0)
    assert out["Lat"].between(53, 53.3).all() and out["Long"].between(-1.7, -1.0).all()
    # centroid of the rectangle in metres, back in degrees: within about 0.001 degrees of the flat-degree one
    assert abs(out["Lat"][2] - expected["Lat"][2]) < 0.001
    assert abs(out["Long"][2] - expected["Long"][2]) < 0.001


def test_zipped_shapefile(tmp_path):
    shp_dir = tmp_path / "shp"
    shp_dir.mkdir()
    districts_for_shapefile().to_file(str(shp_dir / "districts.shp"))
    zpath = tmp_path / "districts.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for f in shp_dir.iterdir():
            z.write(f, f.name)
    out = run(str(zpath), shapeIDfield="name").raise_for_error().output(0)
    assert list(out["name"]) == ["Ashcombe", "Brackenford", "Coldharbour Vale", "Dunmere"]


def test_unknown_id_property_aborts_with_the_properties():
    res = run(SAMPLE, shapeIDfield="District_Code")
    assert res.status == "aborted" and res.error is None
    assert "district_code, district_name, households" in res.final_message


def test_no_file_aborts():
    res = run_block(HERE, [], {})
    assert res.status == "aborted"
    assert "Shapes file" in res.final_message


def test_unreadable_file_aborts(tmp_path):
    bad = tmp_path / "bad.geojson"
    bad.write_text("not json", encoding="utf-8")
    res = run(str(bad))
    assert res.status == "aborted" and "Could not read" in res.final_message


def test_shape_without_geometry_is_kept_with_empty_point(tmp_path):
    path = write_geojson(tmp_path, [
        {"type": "Feature", "properties": {"id": 1}, "geometry": box(0, 50, 1, 51).__geo_interface__},
        {"type": "Feature", "properties": {"id": 2}, "geometry": None},
    ])
    res = run(path, shapeIDfield="id").raise_for_error()
    out = res.output(0)
    assert list(out["id"]) == [1, 2]
    assert out["Lat"].isna().tolist() == [False, True]
    assert "1 without a geometry" in res.final_message


def test_existing_lat_long_properties_are_replaced(tmp_path):
    path = write_geojson(tmp_path, [
        {"type": "Feature", "properties": {"name": "a", "Lat": "old"}, "geometry": box(0, 50, 2, 52).__geo_interface__},
    ])
    out = run(path).raise_for_error().output(0)
    assert list(out.columns) == ["name", "Lat", "Long"]
    assert out["Lat"][0] == 51 and out["Long"][0] == 1


def test_empty_file_gives_no_records(tmp_path):
    path = write_geojson(tmp_path, [])
    res = run(path)
    assert res.status == "committed", res.final_message or res.traceback
    assert len(res.output(0)) == 0 and list(res.output(0).columns) == ["Lat", "Long"]
    # with an ID property chosen, an empty file has no properties to check it against
    res = run(path, shapeIDfield="id")
    assert res.status == "aborted" and "(none)" in res.final_message


def test_many_shapes(tmp_path):
    feats = [{"type": "Feature", "properties": {"cell": i},
              "geometry": box(-2 + (i % 100) * 0.01, 50 + (i // 100) * 0.01,
                              -2 + (i % 100) * 0.01 + 0.01, 50 + (i // 100) * 0.01 + 0.01).__geo_interface__}
             for i in range(20000)]
    path = write_geojson(tmp_path, feats)
    t = time.time()
    out = run(path, shapeIDfield="cell").raise_for_error().output(0)
    assert len(out) == 20000
    assert out["Lat"][0] == pytest.approx(50.005) and out["Long"][0] == pytest.approx(-1.995)
    assert time.time() - t < 30


# ---- shapes as records on the input (GeoJSON or WKT text)

DISTRICTS_CSV = os.path.join(HERE, "sample-data", "districts.csv")


def run_input(data, **options):
    return run_block(HERE, [data], {"geometryField": "Boundary", **options})


def test_input_wkt_sample_matches_the_file():
    res = run_input(DISTRICTS_CSV).raise_for_error()
    out = res.output(0)
    assert list(out.columns) == ["District code", "District name", "Households", "Lat", "Long"]
    from_file = run(SAMPLE).raise_for_error().output(0)
    assert out["Lat"].tolist() == pytest.approx(from_file["Lat"].tolist())
    assert out["Long"].tolist() == pytest.approx(from_file["Long"].tolist())
    assert res.final_message == "4 shapes"


def test_input_id_field_and_point_inside():
    out = run_input(DISTRICTS_CSV, inputIdField="District name", pointType="inside").raise_for_error().output(0)
    assert list(out.columns) == ["District name", "Lat", "Long"]
    assert (out["Lat"][1], out["Long"][1]) == pytest.approx((53.2, -1.23))


def test_input_geojson_text_and_mixed_with_wkt():
    data = pd.DataFrame({"Id": ["a", "b", "c", "d", "e"], "Boundary": [
        json.dumps(box(0, 50, 2, 52).__geo_interface__),
        json.dumps({"type": "Feature", "properties": {}, "geometry": box(10, 50, 12, 52).__geo_interface__}),
        box(20, 50, 22, 52).wkt,
        "not a shape",
        None,
    ]})
    res = run_input(data).raise_for_error()
    out = res.output(0)
    assert out["Long"].tolist()[:3] == pytest.approx([1, 11, 21]) and out["Lat"].tolist()[:3] == pytest.approx([51] * 3)
    assert out["Lat"][3:].isna().all()
    assert "2 without a geometry" in res.final_message and "1 geometry values were not GeoJSON or WKT" in res.final_message


def test_input_takes_precedence_over_the_file():
    out = run_block(HERE, [DISTRICTS_CSV], {"geometryField": "Boundary", "geojsonfile": "/no/such/file.geojson"})
    assert len(out.raise_for_error().output(0)) == 4


def test_input_without_geometry_field_uses_the_file_or_asks_for_it():
    out = run_block(HERE, [DISTRICTS_CSV], {"geojsonfile": SAMPLE}).raise_for_error().output(0)
    assert list(out.columns) == ["district_code", "district_name", "households", "Lat", "Long"]
    res = run_block(HERE, [DISTRICTS_CSV], {})
    assert res.status == "aborted" and "Geometry field" in res.final_message


def test_input_unknown_fields_abort():
    for opts in ({"geometryField": "Shape"}, {"geometryField": "Boundary", "inputIdField": "Code"},
                 {"geometryField": "Boundary", "inputIdField": "Boundary"}):
        res = run_block(HERE, [DISTRICTS_CSV], opts)
        assert res.status == "aborted" and res.error is None, opts


def test_input_empty():
    data = pd.DataFrame({"Id": pd.Series([], dtype=object), "Boundary": pd.Series([], dtype=object)})
    out = run_input(data).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["Id", "Lat", "Long"]
