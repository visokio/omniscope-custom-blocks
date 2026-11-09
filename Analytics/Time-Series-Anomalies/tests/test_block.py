import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "daily-orders.csv")


def series(n=120, seed=0, weekly=True):
    rng = np.random.default_rng(seed)
    d = pd.date_range("2025-01-06", periods=n, freq="D")
    f = np.array([1, 1, 1, 1, 1.1, 1.6, 0.5]) if weekly else np.ones(7)
    v = 100 * f[d.dayofweek] + rng.normal(0, 3, n)
    return pd.DataFrame({"d": d.strftime("%Y-%m-%d"), "v": v})


def run(df, **opts):
    return run_block(HERE, df, {"date_field": "d", "value_field": "v", **opts})


def test_spike_and_dip_found_weekday_pattern_ignored():
    df = series()
    df.loc[50, "v"] += 60
    df.loc[80, "v"] -= 50
    res = run(df).raise_for_error()
    a = res.output(1)
    assert set(a["Period"].dt.strftime("%Y-%m-%d")) == {df.loc[50, "d"], df.loc[80, "d"]}
    assert a.set_index(a["Period"].dt.strftime("%Y-%m-%d")).loc[df.loc[50, "d"], "Anomaly"] == "Spike"
    s = res.output(0)
    assert s["Weekday Effect"].abs().max() > 30  # Saturday / Sunday effect learned
    no = run(df, seasonality="NONE").raise_for_error().output(1)
    assert len(no) > 2  # without the weekday effect, weekends look unusual


def test_direction_threshold_and_trailing():
    df = series(seed=1)
    df.loc[60, "v"] += 60
    df.loc[90, "v"] -= 50
    assert set(run(df, direction="UP").raise_for_error().output(1)["Anomaly"]) == {"Spike"}
    assert set(run(df, direction="DOWN").raise_for_error().output(1)["Anomaly"]) == {"Dip"}
    assert len(run(df, threshold=50).raise_for_error().output(1)) == 0
    t = run(df, mode="TRAILING").raise_for_error().output(0)
    assert (t["Anomaly"].iloc[:14] == "Not scored").all()  # trailing needs history first


def test_aggregation_and_missing_periods():
    rows = pd.DataFrame({"d": ["2025-01-01", "2025-01-01", "2025-01-02", "2025-01-04"], "v": [1.0, 2.0, 5.0, 1.0], "s": ["a", "a", "a", "a"]})
    o = run(rows, series_fields=["s"], min_history=3).raise_for_error().output(0)
    assert o["Value"].tolist() == [3.0, 5.0, 0.0, 1.0]  # summed; 3 January filled with zero
    o = run(rows, aggregation="COUNT", value_field="").raise_for_error().output(0)
    assert o["Value"].tolist() == [2.0, 1.0, 0.0, 1.0]
    o = run(rows, aggregation="MEAN").raise_for_error().output(0)
    assert o["Value"].iloc[0] == 1.5 and pd.isna(o["Value"].iloc[2])
    w = run(series(70), period="WEEK").raise_for_error().output(0)
    assert len(w) == 10 and (w["Weekday Effect"] == 0).all()


def test_sample_orders():
    res = run_block(HERE, SAMPLE, {"date_field": "Order Date", "value_field": "Orders", "series_fields": ["Region"]}).raise_for_error()
    a = res.output(1)
    got = set(zip(a["Region"], a["Period"].dt.strftime("%m-%d")))
    planted = {("South", "03-14"), ("South", "03-15"), ("North", "11-28"), ("South", "11-28"), ("Scotland", "11-28"), ("North", "06-09"),
               ("Scotland", "09-01"), ("Scotland", "09-02"), ("Scotland", "09-03"), ("North", "08-20")}
    assert planted <= got and len(got - planted) <= 2
    s = res.output(2).set_index("Region")
    assert s.loc["North", "Periods"] == 365


def test_bad_inputs_and_empty():
    df = series(30)
    assert run(df, date_field="zz").status == "aborted"
    assert run(df, value_field="").status == "aborted"
    assert run(df, window=2).status == "aborted"
    res = run(df.iloc[0:0]).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0
    res = run(df.assign(v="x")).raise_for_error()
    assert (res.output(0)["Value"] == 0).all()  # text values sum to nothing; counted as zero
    flat = pd.DataFrame({"d": pd.date_range("2025-01-01", periods=40).strftime("%Y-%m-%d"), "v": 5.0})
    flat.loc[30, "v"] = 9.0
    a = run(flat, seasonality="NONE").raise_for_error().output(1)
    assert len(a) == 1 and a["Anomaly"].iloc[0] == "Spike"


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    d = pd.date_range("2023-01-01", periods=730, freq="D")
    df = pd.DataFrame({"d": np.tile(d, 300), "s": np.repeat([f"s{i}" for i in range(300)], 730), "v": rng.normal(100, 10, 730 * 300)})
    t0 = time.time()
    res = run(df, series_fields=["s"]).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(2)) == 300
