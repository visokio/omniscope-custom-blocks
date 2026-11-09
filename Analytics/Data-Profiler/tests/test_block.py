import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "customer-orders.csv")

PROFILE_FIELDS = ["Field", "Type", "Records", "Missing", "Missing %", "Distinct", "Most common", "Most common count",
                  "Mean", "Std dev", "Min", "Lower quartile", "Median", "Upper quartile", "Max", "Skewness",
                  "First date", "Last date", "Anomalies"]


def profile_of(res):
    return res.output(0).set_index("Field")


def test_sample_profile():
    res = run_block(HERE, SAMPLE, {}).raise_for_error()
    prof = res.output(0)
    assert list(prof.columns) == PROFILE_FIELDS
    assert prof["Field"].tolist() == ["Order ID", "Order Date", "Region", "Channel", "Quantity", "Unit Price",
                                      "Discount %", "Delivery Days", "Order Value"]
    p = prof.set_index("Field")
    assert p["Type"].to_dict() == {"Order ID": "Text", "Order Date": "Date", "Region": "Text", "Channel": "Text",
                                   "Quantity": "Integer", "Unit Price": "Decimal", "Discount %": "Integer",
                                   "Delivery Days": "Integer", "Order Value": "Decimal"}
    assert set(p["Records"]) == {80}
    assert p.loc["Region", "Missing"] == 3 and p.loc["Discount %", "Missing"] == 4
    assert p.loc["Order Date", "Missing"] == 1 and p.loc["Discount %", "Missing %"] == 5.0
    # the duplicated order number shows up as 79 distinct values, the duplicate as the most common
    assert p.loc["Order ID", "Distinct"] == 79
    assert (p.loc["Order ID", "Most common"], p.loc["Order ID", "Most common count"]) == ("ORD-3017", 2)
    assert (p.loc["Channel", "Most common"], p.loc["Channel", "Most common count"]) == ("Online", 46)
    # every value different: no most common value
    assert pd.isna(p.loc["Unit Price", "Most common"]) and pd.isna(p.loc["Unit Price", "Most common count"])
    assert p.loc["Quantity", "Max"] == 120 and p.loc["Delivery Days", "Min"] == -3
    assert p.loc["Quantity", "Anomalies"] == 1 and p.loc["Delivery Days", "Anomalies"] == 1
    assert p.loc["Order Value", "Anomalies"] == 1 and p.loc["Unit Price", "Anomalies"] == 0
    assert str(p.loc["Order Date", "First date"].date()) == "2025-01-06"
    assert str(p.loc["Order Date", "Last date"].date()) == "2025-06-24"

    recs = res.output(1)
    assert len(recs) == 80
    flagged = recs[recs["Anomaly count"] > 0]
    assert flagged["Order ID"].tolist() == ["ORD-3024", "ORD-3039"]
    assert flagged["Anomaly count"].tolist() == [2, 1]  # 120 units: Quantity and Order Value
    assert recs.columns[-1] == "Anomaly count"
    assert recs.columns[:9].tolist() == p.index.tolist()
    assert "2 of 80 records" in res.final_message


def test_types_are_omniscope_types_not_pandas_dtypes():
    # The original wrote pandas dtype names: "Int64", "float64", "object", "datetime64[us, UTC]", "bool"
    df = pd.DataFrame({"id": ["a", "b", "c"], "n": [1, 2, None], "x": [1.5, 2.5, 3.5],
                       "d": pd.to_datetime(["2025-01-01", "2025-02-01", None]), "b": [True, False, True]})
    p = profile_of(run_block(HERE, df, {}).raise_for_error())
    assert p["Type"].tolist() == ["Text", "Integer", "Decimal", "Date", "Boolean"]


def test_statistics_are_numbers_and_the_schema_is_fixed():
    # The original's Mean, Min, quartiles and Max were text-like (numbers and dates mixed in one field), and a
    # text-only input gave no Mean or Std dev fields at all
    df = pd.DataFrame({"n": [1.0, 2.0, 3.0, 4.0], "d": pd.to_datetime(["2025-01-01"] * 4)})
    prof = run_block(HERE, df, {}).raise_for_error().output(0)
    for c in ("Mean", "Std dev", "Min", "Lower quartile", "Median", "Upper quartile", "Max", "Skewness"):
        assert pd.api.types.is_float_dtype(prof[c]), c
    assert pd.api.types.is_datetime64_any_dtype(prof["First date"])
    text_only = run_block(HERE, pd.DataFrame({"t": ["a", "b", "a"]}), {}).raise_for_error().output(0)
    assert list(text_only.columns) == PROFILE_FIELDS
    assert text_only.loc[0, "Most common"] == "a" and text_only.loc[0, "Most common count"] == 2


def test_z_scores_use_the_standard_deviation_shown_and_p_values_are_two_sided():
    # The original's z-scores used a different standard deviation from the one in its statistics, and its
    # "likelihood" was 0.5 for a value exactly at the mean
    df = pd.DataFrame({"v": [2.0, 4.0, 6.0, 8.0, 10.0]})
    res = run_block(HERE, df, {}).raise_for_error()
    std = profile_of(res).loc["v", "Std dev"]
    recs = res.output(1)
    assert np.allclose(recs["v_z_score"], (df["v"] - 6.0) / std)
    assert recs.loc[2, "v_p_value"] == 1.0
    assert 0 < recs.loc[0, "v_p_value"] < recs.loc[1, "v_p_value"] < 1
    assert list(recs.columns) == ["v", "v_z_score", "v_anomaly", "v_p_value", "Anomaly count"]


def test_threshold_and_anomaly_flags():
    # 20 values of 10 and one of 20: z = 4.36 for the odd one (sample standard deviation)
    df = pd.DataFrame({"v": [10] * 20 + [20], "k": range(21)})
    recs = run_block(HERE, df, {"fields": ["v"]}).raise_for_error().output(1)
    assert str(recs["v_anomaly"].dtype) == "Int64"  # whole numbers, not decimals as before
    assert recs["v_anomaly"].tolist() == [0] * 20 + [1]
    z = recs.loc[20, "v_z_score"]
    assert round(z, 2) == 4.36
    # a value exactly at the threshold is flagged ("at least", as the description says)
    at = run_block(HERE, df, {"fields": ["v"], "threshold": float(z)}).raise_for_error().output(1)
    assert at["v_anomaly"].sum() == 1
    above = run_block(HERE, df, {"fields": ["v"], "threshold": float(z) + 0.01}).raise_for_error().output(1)
    assert above["v_anomaly"].sum() == 0
    # only the chosen field is profiled and scored
    res = run_block(HERE, df, {"fields": ["v"]}).raise_for_error()
    assert res.output(0)["Field"].tolist() == ["v"] and "k_z_score" not in res.output(1).columns


def test_missing_values_constant_fields_and_booleans():
    df = pd.DataFrame({"v": [1.0, None, 3.0, 5.0], "c": [7, 7, 7, 7], "b": [True, False, True, True]})
    res = run_block(HERE, df, {}).raise_for_error()
    recs = res.output(1)
    assert pd.isna(recs.loc[1, "v_z_score"]) and pd.isna(recs.loc[1, "v_anomaly"]) and pd.isna(recs.loc[1, "v_p_value"])
    assert recs["c_z_score"].isna().all()  # no spread: no z-score
    assert "b_z_score" not in recs.columns  # the original scored True/False as 1/0
    p = profile_of(res)
    assert p.loc["b", "Most common"] == "True" and p.loc["b", "Most common count"] == 3
    assert p.loc["c", "Std dev"] == 0 and p.loc["c", "Anomalies"] == 0


def test_empty_input():
    df = pd.DataFrame({"a": pd.Series([], dtype="float64"), "t": pd.Series([], dtype=object)})
    res = run_block(HERE, df, {}).raise_for_error()
    prof = res.output(0)
    assert prof["Field"].tolist() == ["a", "t"] and prof["Records"].tolist() == [0, 0]
    assert len(res.output(1)) == 0 and "a_z_score" in res.output(1).columns


def test_bad_options_and_no_input_abort():
    # The original raised AttributeError with no input
    res = run_block(HERE, None, {})
    assert res.status == "aborted" and "Connect" in res.final_message
    df = pd.DataFrame({"v": [1.0, 2.0]})
    res = run_block(HERE, df, {"threshold": 0})
    assert res.status == "aborted" and "greater than 0" in res.final_message
    res = run_block(HERE, df, {"fields": ["nope"]})
    assert res.status == "aborted" and "nope" in res.final_message


def test_large_input():
    n = 200_000
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"id": [f"R{i}" for i in range(n)], "x": rng.normal(100, 10, n),
                       "k": rng.integers(0, 50, n), "cat": rng.choice(["a", "b", "c"], n),
                       "d": pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")})
    t0 = time.time()
    res = run_block(HERE, df, {}).raise_for_error()
    assert time.time() - t0 < 60
    assert len(res.output(1)) == n
    p = profile_of(res)
    assert p.loc["id", "Distinct"] == n and abs(p.loc["x", "Mean"] - 100) < 0.2
