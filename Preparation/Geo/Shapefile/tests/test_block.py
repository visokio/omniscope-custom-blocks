import json
import os
import time
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
REGIONS = os.path.join(HERE, "sample-data", "districts.geojson")
DEPOTS = os.path.join(HERE, "sample-data", "depots.csv")
POINT_OPTIONS = {"latitude_field": "Latitude", "longitude_field": "Longitude"}


def run(points, shp_file=REGIONS, **options):
    return run_block(HERE, [points] if points is not None else [], {"shp_file": shp_file, **options})


def write_geojson(tmp_path, features, name="regions.geojson"):
    path = tmp_path / name
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    return str(path)


def districts_for_shapefile():
    """The sample districts, renamed for a shapefile (which cuts property names to 10 characters)."""
    return gpd.read_file(REGIONS).rename(columns={"district_code": "code", "district_name": "name"})


EXPECTED = {
    "North yard": "Ashcombe", "Mill lane": "Ashcombe", "Station road": "Brackenford", "Old forge": "Brackenford",
    "Quarry gate": "Coldharbour Vale", "Bridge end": "Coldharbour Vale", "Low common": "Dunmere",
    "Marsh farm": "Dunmere", "Island store": "Dunmere", "Canal wharf": "Brackenford",
    "Far point": None, "Unknown site": None,
}


def test_sample_points_get_their_district():
    res = run(DEPOTS, label="district_name", **POINT_OPTIONS).raise_for_error()
    out = res.output(0)
    assert list(out.columns) == ["Depot", "Latitude", "Longitude", "Vans", "regions"]
    got = {d: (r if isinstance(r, str) else None) for d, r in zip(out["Depot"], out["regions"])}
    assert got == EXPECTED
    assert res.final_message == "10 of 12 points are in a region (4 regions)."


def test_regions_output_lists_properties_and_shapes():
    res = run(DEPOTS).raise_for_error()
    regions = res.output(1)
    assert list(regions.columns) == ["district_code", "district_name", "households", "geometry"]
    assert regions["geometry"][3].startswith("MULTIPOLYGON")
    assert 0 not in res.outputs  # no join until the label and point fields are chosen
    assert "Choose the label" in res.final_message


def test_empty_text_options_count_as_not_set():
    res = run(DEPOTS, label="", latitude_field="", longitude_field="").raise_for_error()
    assert 0 not in res.outputs and len(res.output(1)) == 4


def test_projected_shapefile(tmp_path):
    # the same districts in British National Grid (metres): points in degrees must still find them
    path = str(tmp_path / "districts-bng.shp")
    districts_for_shapefile().to_crs("EPSG:27700").to_file(path)
    out = run(DEPOTS, shp_file=path, label="name", **POINT_OPTIONS).raise_for_error().output(0)
    got = {d: (r if isinstance(r, str) else None) for d, r in zip(out["Depot"], out["regions"])}
    assert got == EXPECTED


def test_zipped_shapefile(tmp_path):
    shp_dir = tmp_path / "shp"
    shp_dir.mkdir()
    districts_for_shapefile().to_file(str(shp_dir / "districts.shp"))
    zpath = tmp_path / "districts.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for f in shp_dir.iterdir():
            z.write(f, f.name)
    out = run(DEPOTS, shp_file=str(zpath), label="code", **POINT_OPTIONS).raise_for_error().output(0)
    assert out["regions"].notna().sum() == 10


def test_numeric_labels_and_overlapping_regions(tmp_path):
    path = write_geojson(tmp_path, [
        {"type": "Feature", "properties": {"zone": 7}, "geometry": box(0, 50, 2, 52).__geo_interface__},
        {"type": "Feature", "properties": {"zone": 3}, "geometry": box(1, 51, 3, 53).__geo_interface__},
        {"type": "Feature", "properties": {"zone": None}, "geometry": box(0, 50, 3, 53).__geo_interface__},
    ])
    points = pd.DataFrame({"Latitude": [50.5, 51.5, 52.5, 49.0], "Longitude": [0.5, 1.5, 2.5, 0.0]})
    out = run(points, shp_file=path, label="zone", **POINT_OPTIONS).raise_for_error().output(0)
    assert out["regions"].tolist()[:3] == ["7", "7,3", "3"]
    assert pd.isna(out["regions"][3])


def test_points_keep_their_order_and_types():
    points = pd.DataFrame({"Latitude": [53.03, 53.21], "Longitude": [-1.28, -1.52], "N": [1, 2]})
    out = run(points, label="district_code", **POINT_OPTIONS).raise_for_error().output(0)
    assert out["regions"].tolist() == ["D04", "D01"]
    assert str(out["N"].dtype) == "Int64"


def test_unknown_label_aborts_with_the_properties():
    res = run(DEPOTS, label="Name", **POINT_OPTIONS)
    assert res.status == "aborted" and res.error is None
    assert "district_code, district_name, households" in res.final_message


def test_text_coordinates_abort():
    points = pd.DataFrame({"Latitude": ["53.2N"], "Longitude": ["1.5W"]})
    res = run(points, label="district_code", **POINT_OPTIONS)
    assert res.status == "aborted" and "number field" in res.final_message


def test_missing_point_field_or_input_aborts():
    res = run(DEPOTS, label="district_code", latitude_field="Lat", longitude_field="Longitude")
    assert res.status == "aborted" and "\"Lat\"" in res.final_message
    res = run(None, label="district_code", **POINT_OPTIONS)
    assert res.status == "aborted" and "Connect" in res.final_message


def test_no_file_or_bad_file_aborts(tmp_path):
    res = run_block(HERE, [DEPOTS], {})
    assert res.status == "aborted" and "Shapefile" in res.final_message
    bad = tmp_path / "bad.geojson"
    bad.write_text("not json", encoding="utf-8")
    res = run(DEPOTS, shp_file=str(bad))
    assert res.status == "aborted" and "Could not read" in res.final_message


def test_empty_input():
    points = pd.DataFrame({"Latitude": pd.Series([], dtype="float64"), "Longitude": pd.Series([], dtype="float64")})
    out = run(points, label="district_code", **POINT_OPTIONS).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["Latitude", "Longitude", "regions"]


def test_many_points_and_regions(tmp_path):
    # 2,500 square regions and 100,000 points
    feats = [{"type": "Feature", "properties": {"cell": f"C{i}"},
              "geometry": box(i % 50, i // 50, i % 50 + 1, i // 50 + 1).__geo_interface__} for i in range(2500)]
    path = write_geojson(tmp_path, feats)
    rng = np.random.default_rng(1)
    points = pd.DataFrame({"Latitude": rng.uniform(0.001, 49.999, 100000),
                           "Longitude": rng.uniform(0.001, 49.999, 100000)})
    t = time.time()
    out = run(points, shp_file=path, label="cell", **POINT_OPTIONS).raise_for_error().output(0)
    elapsed = time.time() - t
    assert out["regions"].notna().all()
    first = out.iloc[0]
    assert out["regions"][0] == f"C{int(first.Latitude) * 50 + int(first.Longitude)}"
    assert elapsed < 60


# ---- regions as records on the second input (GeoJSON or WKT text)

DISTRICTS_CSV = os.path.join(HERE, "sample-data", "districts.csv")
INPUT_OPTIONS = {**POINT_OPTIONS, "regionGeometryField": "Boundary", "regionLabelField": "District name"}


def test_regions_from_second_input_match_the_file():
    res = run_block(HERE, [DEPOTS, DISTRICTS_CSV], INPUT_OPTIONS).raise_for_error()
    out = res.output(0)
    got = {d: (r if isinstance(r, str) else None) for d, r in zip(out["Depot"], out["regions"])}
    assert got == EXPECTED
    assert res.final_message == "10 of 12 points are in a region (4 regions)."
    regions = res.output(1)
    assert list(regions.columns) == ["District code", "District name", "Households", "geometry"]


def test_second_input_geojson_text_numeric_labels_and_bad_shapes():
    regions = pd.DataFrame({"Zone": [7, 3, 9], "Shape": [
        json.dumps(box(0, 50, 2, 52).__geo_interface__), box(1, 51, 3, 53).wkt, "POLYGON ((oops"]})
    points = pd.DataFrame({"Latitude": [50.5, 51.5, 52.5], "Longitude": [0.5, 1.5, 2.5]})
    res = run_block(HERE, [points, regions], {**POINT_OPTIONS, "regionGeometryField": "Shape",
                                              "regionLabelField": "Zone"}).raise_for_error()
    assert res.output(0)["regions"].tolist() == ["7", "7,3", "3"]
    assert "1 geometry values were not GeoJSON or WKT" in res.final_message


def test_second_input_takes_precedence_over_the_file():
    out = run_block(HERE, [DEPOTS, DISTRICTS_CSV], {**INPUT_OPTIONS, "shp_file": "/no/such/file.shp"})
    assert out.raise_for_error().output(0)["regions"].notna().sum() == 10


def test_second_input_without_label_writes_only_regions():
    res = run_block(HERE, [DEPOTS, DISTRICTS_CSV], {**POINT_OPTIONS, "regionGeometryField": "Boundary"})
    res.raise_for_error()
    assert 0 not in res.outputs and len(res.output(1)) == 4


def test_second_input_without_geometry_field_uses_the_file_or_asks_for_it():
    out = run_block(HERE, [DEPOTS, DISTRICTS_CSV], {"shp_file": REGIONS, "label": "district_code", **POINT_OPTIONS})
    assert out.raise_for_error().output(0)["regions"].notna().sum() == 10
    res = run_block(HERE, [DEPOTS, DISTRICTS_CSV], POINT_OPTIONS)
    assert res.status == "aborted" and "Region geometry field" in res.final_message


def test_second_input_unknown_or_same_fields_abort():
    for opts in ({"regionGeometryField": "Shape"}, {"regionGeometryField": "Boundary", "regionLabelField": "Name"},
                 {"regionGeometryField": "Boundary", "regionLabelField": "Boundary"}):
        res = run_block(HERE, [DEPOTS, DISTRICTS_CSV], {**POINT_OPTIONS, **opts})
        assert res.status == "aborted" and res.error is None, opts
