import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "deliveries.csv")
O = {"from_lat": "a", "from_lon": "b", "to_lat": "c", "to_lon": "d"}


def run(df, **opts):
    return run_block(HERE, df, {**O, **opts})


def test_known_distances_bearing_and_midpoint():
    df = pd.DataFrame({"a": [0.0, 51.5, 53.7965], "b": [0.0, 0.0, -1.5478], "c": [0.0, 52.5, 53.9590], "d": [1.0, 0.0, -1.0815]})
    o = run(df).raise_for_error().output(0)
    assert abs(o["Distance (km)"].iloc[0] - 111.2) < 0.2 and abs(o["Distance (km)"].iloc[1] - 111.2) < 0.2  # one degree
    assert np.isclose(o["Bearing (degrees)"].iloc[0], 90) and o["Direction"].iloc[1] == "N"
    assert np.isclose(o["Midpoint Latitude"].iloc[1], 52.0) and abs(o["Distance (km)"].iloc[2] - 35.9) < 1
    m = run(df, unit="MILES", road_factor=1.3, speed=30).raise_for_error().output(0)
    assert np.isclose(m["Estimated Minutes"].iloc[0], m["Distance (miles)"].iloc[0] * 1.3 / 30 * 60)


def test_sample_invalid_and_large():
    res = run_block(HERE, SAMPLE, {"from_lat": "Depot Lat", "from_lon": "Depot Lon", "to_lat": "Drop Lat", "to_lon": "Drop Lon"}).raise_for_error()
    o = res.output(0)
    assert o["Valid Coordinates"].tolist().count("No") == 1 and o.set_index("Drop Postcode Area").loc["Aberdeen", "Direction"] == "NE"
    assert run(pd.DataFrame({"a": [100.0], "b": [0.0], "c": [0.0], "d": [0.0]})).raise_for_error().output(0)["Valid Coordinates"].iloc[0] == "No"
    assert run(pd.DataFrame({"a": [1.0]})).status == "aborted"
    rng = np.random.default_rng(0)
    big = pd.DataFrame({k: rng.uniform(50, 58, 500_000) if k in "ac" else rng.uniform(-5, 1, 500_000) for k in "abcd"})
    t0 = time.time()
    run(big).raise_for_error()
    assert time.time() - t0 < 120
