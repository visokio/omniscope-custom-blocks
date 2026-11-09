import json
import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CUST = os.path.join(HERE, "sample-data", "customers.csv")
TERR = os.path.join(HERE, "sample-data", "sales-territories.csv")
F = {"lat_field": "lat", "lon_field": "lon", "geometry_field": "g"}


def run(p, g, **opts):
    return run_block(HERE, [p, g], {**F, **opts})


SQUARE = json.dumps({"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]})
HOLE_WKT = "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0), (4 4, 6 4, 6 6, 4 6, 4 4))"
MULTI = json.dumps({"type": "Feature", "properties": {}, "geometry": {"type": "MultiPolygon", "coordinates": [
    [[[20, 20], [21, 20], [21, 21], [20, 20]]], [[[30, 30], [32, 30], [32, 32], [30, 32], [30, 30]]]]}})


def pts(*xy):
    return pd.DataFrame({"lon": [p[0] for p in xy], "lat": [p[1] for p in xy], "v": [1.5] * len(xy)})


def test_square_hole_multipolygon():
    polys = pd.DataFrame({"name": ["sq", "hole", "multi"], "g": [SQUARE, HOLE_WKT, MULTI]})
    p = pts((5, 5), (1, 1), (31, 31), (50, 50))
    out = run(p, polys, match_mode="ALL").raise_for_error().output(0)
    got = out.groupby("lon")["Polygon: name"].apply(lambda s: sorted(x for x in s if isinstance(x, str))).to_dict()
    assert got[5] == ["sq"]  # (5,5) is in the hole of "hole"
    assert got[1] == ["hole", "sq"] and got[31] == ["multi"] and got[50] == []
    assert out.loc[out.lon == 50, "Match Status"].iloc[0] == "Outside all polygons"


def test_first_mode_and_counts():
    polys = pd.DataFrame({"name": ["sq", "hole"], "g": [SQUARE, HOLE_WKT]})
    res = run(pts((1, 1), (2, 2), (5, 5)), polys, value_field="v").raise_for_error()
    out = res.output(0)
    assert len(out) == 3 and (out["Polygon: name"] == "sq").all()
    assert out["Polygons Containing Point"].tolist() == [2, 2, 1]
    summ = res.output(1).set_index("name")
    assert summ.loc["sq", "Points"] == 3 and summ.loc["hole", "Points"] == 0 and summ.loc["sq", "Total v"] == 4.5


def test_sample_territories():
    res = run_block(HERE, [CUST, TERR], {"lat_field": "Latitude", "lon_field": "Longitude", "geometry_field": "Geometry", "match_mode": "ALL"}).raise_for_error()
    out = res.output(0)
    inside = out[out["Match Status"] == "Inside"]
    assert inside["Customer ID"].is_unique  # territories (with the London hole) do not overlap
    assert res.output(1)["Geometry Status"].eq("OK").all()


def test_bad_geometry_rows_reported_and_bad_points():
    polys = pd.DataFrame({"name": ["ok", "bad"], "g": [SQUARE, "CIRCLE (1 2)"]})
    res = run(pd.DataFrame({"lon": ["1", "x"], "lat": [1.0, 2.0]}), polys).raise_for_error()
    assert res.output(1).set_index("name").loc["bad", "Geometry Status"].startswith("Could not read")
    assert res.output(0)["Match Status"].tolist() == ["Inside", "Invalid coordinates"]
    assert run(pts((1, 1)), pd.DataFrame({"g": ["nonsense"]})).status == "aborted"


def test_empty_and_missing():
    empty = pd.DataFrame({"lon": pd.Series([], dtype="float64"), "lat": pd.Series([], dtype="float64")})
    res = run(empty, pd.DataFrame({"g": [SQUARE]})).raise_for_error()
    assert len(res.output(0)) == 0 and res.output(1)["Points"].iloc[0] == 0
    assert run_block(HERE, [pts((1, 1))], F).status == "aborted"
    assert run(pts((1, 1)), pd.DataFrame({"g": [SQUARE]}), geometry_field="geom").status == "aborted"


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    p = pd.DataFrame({"lon": rng.uniform(-6, 2, 300_000), "lat": rng.uniform(50, 59, 300_000)})
    t0 = time.time()
    res = run_block(HERE, [p, TERR], {"lat_field": "lat", "lon_field": "lon", "geometry_field": "Geometry"}).raise_for_error()
    assert time.time() - t0 < 60 and len(res.output(0)) == 300_000
