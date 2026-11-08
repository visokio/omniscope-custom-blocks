import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CUST = os.path.join(HERE, "sample-data", "customers.csv")
STORES = os.path.join(HERE, "sample-data", "stores.csv")
LL = {"origin_lat": "lat", "origin_lon": "lon", "dest_lat": "lat", "dest_lon": "lon"}


def run(o, d, **opts):
    return run_block(HERE, [o, d], {**LL, **opts})


def pts(*xy, **extra):
    return pd.DataFrame({"lat": [p[0] for p in xy], "lon": [p[1] for p in xy], **extra})


def test_known_distance_and_bearing():
    london, manchester = (51.5074, -0.1278), (53.4808, -2.2426)
    out = run(pts(london), pts(manchester, name=["Manchester"]), unit="KM").raise_for_error().output(0)
    assert abs(out["Distance (km)"].iloc[0] - 262) < 3
    assert out["Direction"].iloc[0] == "NW"
    miles = run(pts(london), pts(manchester), unit="MILES").raise_for_error().output(0)
    assert abs(miles["Distance (miles)"].iloc[0] - 163) < 2


def test_k_nearest_ranked_and_fields_appended():
    o = pts((0.0, 0.0))
    d = pts((0.0, 3.0), (0.0, 1.0), (0.0, 2.0), name=["c", "a", "b"])
    out = run(o, d, k=2).raise_for_error().output(0)
    assert out["Nearest: name"].tolist() == ["a", "b"] and out["Nearest Rank"].tolist() == [1, 2]
    assert out["Distance (km)"].is_monotonic_increasing
    assert "Nearest: lat" in out.columns


def test_max_distance_and_unmatched():
    o = pts((0.0, 0.0), (10.0, 10.0))
    d = pts((0.0, 0.1))
    out = run(o, d, max_distance=50).raise_for_error().output(0)
    assert out["Match Status"].tolist() == ["Found", "None within distance"]
    out = run(o, d, max_distance=50, keep_unmatched=False).raise_for_error().output(0)
    assert len(out) == 1


def test_sample_catchments():
    res = run_block(HERE, [CUST, STORES], {"origin_lat": "Latitude", "origin_lon": "Longitude", "dest_lat": "Latitude",
                                           "dest_lon": "Longitude", "dest_id": "Store", "max_distance": 50}).raise_for_error()
    out, summ = res.output(0), res.output(1)
    assert len(out) == 321
    assert (out["Match Status"] == "Invalid coordinates").sum() == 1
    assert summ["Points Nearest To It"].sum() == (out["Match Status"] == "Found").sum()
    lon = summ.set_index("Store").loc["London Oxford Street"]
    assert lon["Points Nearest To It"] == summ["Points Nearest To It"].max()


def test_wrong_types_text_coordinates_and_out_of_range():
    o = pd.DataFrame({"lat": ["51.5", "abc", "95"], "lon": ["-0.12", "1", "0"]})
    out = run(o, pts((51.5, -0.13))).raise_for_error().output(0)
    assert out["Match Status"].tolist() == ["Found", "Invalid coordinates", "Invalid coordinates"]


def test_empty_inputs():
    empty = pd.DataFrame({"lat": pd.Series([], dtype="float64"), "lon": pd.Series([], dtype="float64")})
    res = run(empty, pts((1.0, 1.0))).raise_for_error()
    assert len(res.output(0)) == 0 and "Distance (km)" in res.output(0).columns
    res = run(pts((1.0, 1.0)), empty).raise_for_error()
    assert res.output(0)["Match Status"].tolist() == ["None within distance"]


def test_missing_inputs_and_fields_abort():
    assert run_block(HERE, [pts((1.0, 1.0))], LL).status == "aborted"
    assert run(pts((1.0, 1.0)), pts((1.0, 1.0)), origin_lat="nope").status == "aborted"


def test_large_input_is_fast():
    rng = np.random.default_rng(4)
    o = pd.DataFrame({"lat": rng.uniform(50, 58, 100_000), "lon": rng.uniform(-5, 1.5, 100_000)})
    d = pd.DataFrame({"lat": rng.uniform(50, 58, 2_000), "lon": rng.uniform(-5, 1.5, 2_000)})
    t0 = time.time()
    out = run(o, d, k=3).raise_for_error().output(0)
    assert time.time() - t0 < 60 and len(out) == 300_000
