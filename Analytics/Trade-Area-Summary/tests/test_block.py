import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SITES = os.path.join(HERE, "sample-data", "branches.csv")
CUST = os.path.join(HERE, "sample-data", "customers.csv")
O = {"site_field": "s", "site_lat": "lat", "site_lon": "lon", "point_lat": "lat", "point_lon": "lon"}


def run(s, p, **opts):
    return run_block(HERE, [s, p], {**O, **opts})


def test_haversine_distance_and_bands():
    s = pd.DataFrame({"s": ["Leeds"], "lat": [53.7965], "lon": [-1.5478]})
    p = pd.DataFrame({"lat": [53.9590], "lon": [-1.0815]})  # York
    r = run(s, p, radii="10, 50").raise_for_error().output(1).iloc[0]
    assert abs(r["Distance To Nearest Site"] - 35.9) < 1.0 and r["Distance Band"] == "10-50 km"
    m = run(s, p, radii="10, 50", unit="MILES").raise_for_error().output(1).iloc[0]
    assert abs(m["Distance To Nearest Site"] - r["Distance To Nearest Site"] / 1.609344) < 0.05


def test_counts_exclusive_and_values():
    s = pd.DataFrame({"s": ["A", "B"], "lat": [51.5, 51.5], "lon": [0.0, 0.02]})  # about 1.4 km apart
    p = pd.DataFrame({"lat": [51.5, 51.5, 51.5, 51.6], "lon": [-0.01, 0.014, 0.04, 0.0], "v": [10.0, 20.0, 30.0, 40.0]})
    res = run(s, p, radii="1, 2", point_value="v").raise_for_error()
    t = res.output(0).set_index(["s", "Radius"])
    assert t.loc[("A", 1.0), "Points Within"] == 2 and t.loc[("A", 1.0), "Value Within"] == 30.0
    assert t.loc[("A", 1.0), "Exclusive Points"] == 1 and t.loc[("A", 1.0), "Shared Points"] == 1
    pts = res.output(1)
    assert pts["Sites Within Largest Radius"].tolist() == [1, 2, 1, 0] and pts["Distance Band"].iloc[3] == "Over 2 km"


def test_sample_and_bad_inputs():
    res = run_block(HERE, [SITES, CUST], {"site_field": "Branch", "site_lat": "Latitude", "site_lon": "Longitude", "point_lat": "Latitude",
                                          "point_lon": "Longitude", "point_value": "Annual Spend (GBP)"}).raise_for_error()
    t = res.output(0)
    assert len(t) == 24 and t[t["Branch"] == "Bradford"]["Points Within"].is_monotonic_increasing
    assert (res.output(1)["Valid Coordinates"] == "No").sum() == 2
    s = pd.DataFrame({"s": ["A"], "lat": [51.5], "lon": [0.0]})
    assert run_block(HERE, s, O).status == "aborted"
    assert run(s, s, radii="a, b").status == "aborted"
    assert run(s, s, radii="0").status == "aborted"
    assert run(s, s, site_lat="zz").status == "aborted"


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    s = pd.DataFrame({"s": [f"S{i}" for i in range(200)], "lat": rng.uniform(50, 55, 200), "lon": rng.uniform(-4, 1, 200)})
    p = pd.DataFrame({"lat": rng.uniform(50, 55, 200_000), "lon": rng.uniform(-4, 1, 200_000)})
    t0 = time.time()
    res = run(s, p).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(1)) == 200_000
