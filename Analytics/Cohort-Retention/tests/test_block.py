import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "subscription-activity.csv")
F = {"customer_field": "c", "date_field": "d"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**F, **opts})


def act():
    # a: Jan, Feb, Apr; b: Jan; c: Feb, Mar
    return pd.DataFrame({"c": ["a", "a", "a", "b", "c", "c", "a"],
                         "d": ["2025-01-05", "2025-02-10", "2025-04-01", "2025-01-20", "2025-02-02", "2025-03-03", "2025-01-25"],
                         "r": [10.5, 10.5, 10.5, 5.5, 20.5, 20.5, 1.0]})


def test_matrix_counts_and_zero_periods():
    res = run(act(), revenue_field="r").raise_for_error()
    m = res.output(0)
    jan = m[m.Cohort == "2025-01"].set_index("Period Number")
    assert jan.loc[0, "Cohort Size"] == 2 and jan.loc[0, "Active Customers"] == 2
    assert jan.loc[1, "Active Customers"] == 1 and jan.loc[2, "Active Customers"] == 0  # March: nobody
    assert jan.loc[3, "Retention"] == 0.5
    assert abs(jan.loc[0, "Revenue"] - 17.0) < 1e-9
    assert abs(jan.loc[3, "Cumulative Revenue Per Customer"] - (17.0 + 10.5 + 10.5) / 2) < 1e-9
    feb = m[m.Cohort == "2025-02"]
    assert feb["Period Number"].max() == 2  # follows up to the last observed period (April)


def test_curve_weighted_and_customers():
    res = run(act()).raise_for_error()
    curve = res.output(1).set_index("Period Number")
    assert curve.loc[0, "Retention (weighted)"] == 1.0
    assert abs(curve.loc[1, "Retention (weighted)"] - 2 / 3) < 1e-9  # jan 1/2 + feb 1/1
    cust = res.output(2).set_index("c")
    assert cust.loc["a", "Periods Active"] == 3 and cust.loc["a", "Active In Latest Period"] == "Yes"
    assert "Total Revenue" not in cust.columns and "Revenue" not in res.output(0).columns


def test_sample_newer_cohorts_retain_better():
    res = run_block(HERE, SAMPLE, {"customer_field": "Account ID", "date_field": "Activity Date", "revenue_field": "Revenue"}).raise_for_error()
    m = res.output(0)
    p1 = m[m["Period Number"] == 1].set_index("Cohort")["Retention"]
    assert p1[["2025-06", "2025-07", "2025-08"]].mean() > p1[["2025-01", "2025-02", "2025-03"]].mean() + 0.05
    assert res.output(2)["Account ID"].is_unique and len(res.output(2)) == 1843


def test_weekly_and_quarterly_labels():
    w = run(act(), period="WEEK").raise_for_error().output(0)
    assert w["Cohort"].iloc[0].startswith("w/c 2024-12-30") or w["Cohort"].iloc[0].startswith("w/c 2025-")
    q = run(act(), period="QUARTER").raise_for_error().output(0)
    assert set(q["Cohort"]) == {"2025 Q1"}


def test_max_periods_and_bad_rows():
    df = act()
    df.loc[len(df)] = ["z", "rubbish", 1.0]
    res = run(df, max_periods=1).raise_for_error()
    assert res.output(0)["Period Number"].max() == 1 and "1 rows skipped" in res.final_message


def test_empty_input_and_bad_fields():
    empty = pd.DataFrame({"c": pd.Series([], dtype=object), "d": pd.Series([], dtype=object)})
    res = run(empty).raise_for_error()
    assert len(res.output(0)) == 0 and "Retention" in res.output(0).columns
    assert run(act(), revenue_field="nope").status == "aborted"
    assert run_block(HERE, act(), {"customer_field": "c"}).status == "aborted"


def test_large_input_is_fast():
    n = 1_000_000
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"c": rng.integers(0, 100_000, n),
                       "d": pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, 900, n), unit="D"), "r": 9.5})
    t0 = time.time()
    res = run(df, revenue_field="r").raise_for_error()
    assert time.time() - t0 < 90 and len(res.output(2)) == df["c"].nunique()
