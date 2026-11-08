import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "online-orders.csv")
F = {"customer_field": "c", "date_field": "d", "amount_field": "a"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**F, **opts})


def tx():
    return pd.DataFrame({"c": ["x", "x", "x", "y", "z", "z"],
                         "d": ["2025-10-01", "2025-10-20", "2025-10-30", "2024-01-15", "2025-06-01", "2025-06-01"],
                         "a": [100.5, 200.5, 300.5, 20.5, 50.5, 60.5], "o": ["1", "2", "3", "4", "5", "5"]})


def test_recency_frequency_monetary():
    out = run(tx()).raise_for_error().output(0).set_index("c")
    assert out.loc["x", "Recency (days)"] == 1 and out.loc["x", "Frequency"] == 3
    assert abs(out.loc["x", "Monetary"] - 601.5) < 1e-9
    assert out.loc["z", "Frequency"] == 2
    assert out.loc["x", "R Score"] == 5 and out.loc["y", "R Score"] < out.loc["x", "R Score"]


def test_order_field_counts_distinct_orders_and_analysis_date():
    out = run(tx(), order_field="o", analysis_date="2025-12-31").raise_for_error().output(0).set_index("c")
    assert out.loc["z", "Frequency"] == 1  # two rows, one order
    assert out.loc["x", "Recency (days)"] == 62
    assert run(tx(), analysis_date="whenever").status == "aborted"


def test_scores_and_segments_on_sample():
    res = run_block(HERE, SAMPLE, {"customer_field": "Customer ID", "date_field": "Order Date", "amount_field": "Order Value",
                                   "order_field": "Order ID"}).raise_for_error()
    out, seg = res.output(0), res.output(1)
    assert len(out) == 600 and out["Customer ID"].is_unique
    assert out[["R Score", "F Score", "M Score"]].stack().between(1, 5).all()
    assert (out["RFM Total"] == out["R Score"] + out["F Score"] + out["M Score"]).all()
    assert seg["Customers"].sum() == 600 and abs(seg["Share Of Revenue"].sum() - 1) < 1e-3
    champ = out[out.Segment == "Champions"]
    lost = out[out.Segment == "Lost"]
    assert champ["Monetary"].mean() > lost["Monetary"].mean() and champ["Recency (days)"].mean() < lost["Recency (days)"].mean()
    assert set(seg["Segment"]) >= {"Champions", "At Risk", "Lost", "New Customers"}


def test_bins_option():
    out = run_block(HERE, SAMPLE, {"customer_field": "Customer ID", "date_field": "Order Date", "amount_field": "Order Value",
                                   "bins": 3}).raise_for_error().output(0)
    assert out["M Score"].max() == 3 and out["RFM Score"].str.len().eq(3).all()


def test_dirty_rows_are_skipped():
    df = tx()
    df.loc[len(df)] = ["w", "not a date", 5.0, "9"]
    df.loc[len(df)] = [None, "2025-01-01", 5.0, "9"]
    res = run(df).raise_for_error()
    assert len(res.output(0)) == 3 and "2 rows skipped" in res.final_message


def test_wrong_types_amount_as_text():
    df = tx().assign(a=["100.5", "x", "300.5", "20.5", "50.5", "60.5"])
    out = run(df).raise_for_error().output(0).set_index("c")
    assert abs(out.loc["x", "Monetary"] - 401.0) < 1e-9


def test_empty_input_and_bad_options():
    empty = pd.DataFrame({"c": pd.Series([], dtype=object), "d": pd.Series([], dtype=object), "a": pd.Series([], dtype="float64")})
    res = run(empty).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0 and "Segment" in res.output(1).columns
    assert run(tx(), amount_field="nope").status == "aborted"
    assert run(tx(), bins=1).status == "aborted"


def test_large_input_is_fast():
    n = 1_000_000
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"c": rng.integers(0, 50_000, n), "d": pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 700, n), unit="D"),
                       "a": rng.gamma(2, 30, n)})
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 90 and len(res.output(0)) == 50_000
