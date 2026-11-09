import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "daily-product-sales.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"date_field": "d", **opts})


def frame():
    return pd.DataFrame({"d": ["2025-01-01", "2025-01-04", "2025-01-02", "2025-01-03"], "g": ["a", "a", "b", "b"],
                         "v": [10.5, 40.5, 5.5, 7.5], "cat": ["x", "x", "y", "y"]})


def test_zero_fill_per_series():
    res = run(frame(), group_fields=["g"], value_fields=["v"]).raise_for_error()
    out = res.output(0)
    a = out[out.g == "a"]
    assert a["Period"].tolist() == ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]
    assert a["v"].tolist() == [10.5, 0.0, 0.0, 40.5] and a["Is Inserted"].tolist() == [0, 1, 1, 0]
    assert a["cat"].tolist() == ["x"] * 4  # carried forward
    assert len(out[out.g == "b"]) == 2  # b has no gap within its own span
    gaps = res.output(1).set_index("g")
    assert gaps.loc["a", "Periods Inserted"] == 2 and gaps.loc["a", "Longest Gap (periods)"] == 2


def test_all_span_aligns_series_and_previous_fill():
    out = run(frame(), group_fields=["g"], value_fields=["v"], span="ALL", fill_method="PREVIOUS").raise_for_error().output(0)
    b = out[out.g == "b"]
    assert b["Period"].tolist() == ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"]
    assert pd.isna(b["v"].iloc[0]) and b["v"].iloc[3] == 7.5


def test_linear_interpolation_and_leave():
    out = run(frame(), group_fields=["g"], value_fields=["v"], fill_method="LINEAR").raise_for_error().output(0)
    assert out[out.g == "a"]["v"].tolist() == [10.5, 20.5, 30.5, 40.5]
    out = run(frame(), group_fields=["g"], value_fields=["v"], fill_method="LEAVE").raise_for_error().output(0)
    assert out[out.g == "a"]["v"].isna().sum() == 2


def test_monthly_and_weekly_frequency():
    df = pd.DataFrame({"d": ["2025-01-15", "2025-04-02"], "v": [1.5, 2.5]})
    m = run(df, value_fields=["v"], frequency="MONTH").raise_for_error().output(0)
    assert m["Period"].tolist() == ["2025-01", "2025-02", "2025-03", "2025-04"]
    w = run(df, value_fields=["v"], frequency="WEEK").raise_for_error().output(0)
    assert len(w) == 12 and w["d"].iloc[1].dayofweek == 0  # inserted week starts on Monday


def test_custom_range_and_integer_values_stay_integer():
    df = pd.DataFrame({"d": pd.to_datetime(["2025-03-02", "2025-03-03"]), "n": pd.array([3, 4], dtype="Int64")})
    out = run(df, value_fields=["n"], span="CUSTOM", range_start="2025-03-01", range_end="2025-03-05").raise_for_error().output(0)
    assert len(out) == 5 and out["n"].dtype == "Int64" and out["n"].tolist() == [0, 3, 4, 0, 0]
    assert run(df, value_fields=["n"], span="CUSTOM", range_start="not a date").status == "aborted"


def test_sample_data():
    res = run_block(HERE, SAMPLE, {"date_field": "Date", "group_fields": ["Product"], "value_fields": ["Units Sold"], "span": "ALL"}).raise_for_error()
    out = res.output(0)
    assert len(out) == 93 and out.groupby("Product").size().eq(31).all()
    assert out["Category"].notna().all()


def test_empty_input_and_bad_dates():
    res = run(pd.DataFrame({"d": pd.Series([], dtype=object), "v": pd.Series([], dtype="float64")}), value_fields=["v"]).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0
    df = pd.DataFrame({"d": ["2025-01-01", "garbage", "2025-01-03"], "v": [1.5, 2.5, 3.5]})
    res = run(df, value_fields=["v"]).raise_for_error()
    assert len(res.output(0)) == 4 and "no valid date" in res.final_message


def test_missing_field_aborts():
    assert run(frame(), value_fields=["nope"]).status == "aborted"
    assert run_block(HERE, frame(), {"date_field": "zzz"}).status == "aborted"


def test_large_input_is_fast():
    rng = np.random.default_rng(1)
    days = pd.date_range("2024-01-01", "2025-12-31")
    rows = 2000 * len(days)
    keep = rng.random(rows) < 0.6
    df = pd.DataFrame({"d": np.tile(days.values, 2000)[keep], "g": np.repeat(np.arange(2000), len(days))[keep], "v": 1.5})
    t0 = time.time()
    out = run(df, group_fields=["g"], value_fields=["v"], span="ALL").raise_for_error().output(0)
    assert time.time() - t0 < 120 and len(out) == rows
