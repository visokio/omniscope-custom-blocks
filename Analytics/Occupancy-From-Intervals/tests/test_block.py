import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "ward-stays.csv")
IV = pd.DataFrame({"s": ["2025-01-01 10:00", "2025-01-01 10:30", "2025-01-01 11:00"], "e": ["2025-01-01 12:00", "2025-01-01 11:00", None], "g": ["x", "x", "x"]})


def run(df, **opts):
    return run_block(HERE, df, {"start_field": "s", "end_field": "e", **opts})


def test_exact_time_weighted_average_and_peak():
    res = run(IV, as_of="2025-01-01 13:00", capacity=1).raise_for_error()
    o = res.output(0)
    h10 = o[o["Bucket Start"].dt.strftime("%H") == "10"].iloc[0]
    assert np.isclose(h10["Average Occupancy"], 1.5) and h10["Peak Occupancy"] == 2 and h10["Arrivals"] == 2
    h11 = o[o["Bucket Start"].dt.strftime("%H") == "11"].iloc[0]
    assert np.isclose(h11["Average Occupancy"], 2.0) and h11["Departures"] == 1 and h11["Over Capacity"] == "Yes"
    s = res.output(1).iloc[0]
    assert s["Peak Occupancy"] == 2 and np.isclose(s["Hours Over Capacity"], 1.5) and s["To"].strftime("%H:%M") == "13:00"


def test_groups_weights_capacity_by_group_and_days():
    df = pd.concat([IV, IV.assign(g="y")])
    df["w"] = [1, 1, 1, 2, 2, 2]
    res = run(df, group_field="g", weight_field="w", capacity_by_group="x=3, y=3", as_of="2025-01-01 13:00").raise_for_error()
    s = res.output(1).set_index("g")
    assert s.loc["y", "Peak Occupancy"] == 4 and s.loc["x", "Hours Over Capacity"] == 0 and s.loc["y", "Hours Over Capacity"] > 0
    d = run(IV, bucket="DAY", as_of="2025-01-01 13:00").raise_for_error().output(0)
    assert len(d) == 1 and np.isclose(d["Average Occupancy"].iloc[0], (2 + 0.5 + 2) / 24)


def test_sample_and_bad_inputs():
    res = run_block(HERE, SAMPLE, {"start_field": "Admitted", "end_field": "Discharged", "group_field": "Ward", "capacity_by_group": "Ward A=24, Ward B=18, Ward C=30",
                                   "as_of": "2025-11-30 23:59"}).raise_for_error()
    assert len(res.output(1)) == 3 and (res.output(1)["Average Utilisation"] < 1.2).all()
    assert run(IV, start_field="zz").status == "aborted"
    assert run(IV, capacity_by_group="x is ten").status == "aborted"
    r = run(IV.assign(s=["bad", "2025-01-01 10:30", "2025-01-01 11:00"])).raise_for_error()
    assert "skipped" in r.final_message


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    st = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365 * 24 * 60, 200_000), unit="m")
    df = pd.DataFrame({"s": st, "e": st + pd.to_timedelta(rng.integers(5, 600, 200_000), unit="m"), "g": rng.choice(list("abcdefgh"), 200_000)})
    t0 = time.time()
    res = run(df, group_field="g").raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(1)) == 8
