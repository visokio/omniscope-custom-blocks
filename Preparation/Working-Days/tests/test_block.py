import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "support-tickets.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"start_field": "s", **opts})


def holidays(region, year):
    df = pd.DataFrame({"s": [f"{year}-06-01"], "e": [f"{year}-06-02"]})
    cal = run(df, end_field="e", region=region).raise_for_error().output(1)
    cal = cal[cal["Date"].dt.year == year]
    return sorted(cal["Date"].dt.strftime("%Y-%m-%d"))


def test_england_wales_known_years():
    assert holidays("ENGLAND_WALES", 2025) == ["2025-01-01", "2025-04-18", "2025-04-21", "2025-05-05", "2025-05-26",
                                                "2025-08-25", "2025-12-25", "2025-12-26"]
    assert holidays("ENGLAND_WALES", 2022) == ["2022-01-03", "2022-04-15", "2022-04-18", "2022-05-02", "2022-06-02",
                                                "2022-06-03", "2022-08-29", "2022-09-19", "2022-12-26", "2022-12-27"]
    assert holidays("ENGLAND_WALES", 2021)[-2:] == ["2021-12-27", "2021-12-28"]
    assert "2020-05-08" in holidays("ENGLAND_WALES", 2020) and "2020-05-04" not in holidays("ENGLAND_WALES", 2020)
    assert "2023-05-08" in holidays("ENGLAND_WALES", 2023)


def test_scotland_and_ni():
    sc = holidays("SCOTLAND", 2025)
    assert {"2025-01-02", "2025-08-04", "2025-12-01"} <= set(sc) and "2025-04-21" not in sc
    ni = holidays("NI", 2025)
    assert {"2025-03-17", "2025-07-14", "2025-04-21"} <= set(ni)  # Boyne on Sat 12th -> Mon 14th


def test_us_federal():
    assert holidays("US", 2025) == ["2025-01-01", "2025-01-20", "2025-02-17", "2025-05-26", "2025-06-19", "2025-07-04",
                                    "2025-09-01", "2025-10-13", "2025-11-11", "2025-11-27", "2025-12-25"]
    assert "2026-07-03" in holidays("US", 2026)  # 4 July 2026 is a Saturday


def test_count_over_easter_and_christmas():
    df = pd.DataFrame({"s": ["2025-04-17", "2025-12-22", "2025-06-02"], "e": ["2025-04-23", "2025-12-31", "2025-06-06"]})
    out = run(df, end_field="e").raise_for_error().output(0)
    assert out["Working Days"].tolist() == [3, 6, 5]  # Thu, Tue, Wed ; Mon-Wed + Mon-Wed ; Mon-Fri
    out = run(df, end_field="e", include_start=False).raise_for_error().output(0)
    assert out["Working Days"].tolist()[2] == 4


def test_add_days_due_date_and_sla():
    df = pd.DataFrame({"s": ["2025-04-17", "2025-12-24"], "e": ["2025-04-24", "2025-12-29"], "n": [2, 1]})
    out = run(df, end_field="e", days_field="n").raise_for_error().output(0)
    assert out["Due Date"].dt.strftime("%Y-%m-%d").tolist() == ["2025-04-23", "2025-12-29"]
    assert out["Met Target"].tolist() == ["No", "Yes"] and out["Working Days Late"].tolist() == [1, 0]


def test_custom_closures_and_weekend_options():
    df = pd.DataFrame({"s": ["2025-12-29"], "e": ["2025-12-31"]})
    assert run(df, end_field="e", custom_holidays="2025-12-29, 2025-12-30").raise_for_error().output(0)["Working Days"].iloc[0] == 1
    fs = pd.DataFrame({"s": ["2025-06-05"], "e": ["2025-06-08"]})  # Thu..Sun
    assert run(fs, end_field="e", weekend="FRI_SAT", region="NONE").raise_for_error().output(0)["Working Days"].iloc[0] == 2
    assert run(df, end_field="e", custom_holidays="soon").status == "aborted"


def test_sample_tickets_day_first_text():
    res = run_block(HERE, SAMPLE, {"start_field": "Raised", "end_field": "Resolved", "days_field": "SLA Working Days"}).raise_for_error()
    out = res.output(0)
    assert out["Working Days"].notna().all() and set(out["Met Target"]) <= {"Yes", "No"}
    assert (out["Working Days"] <= out["Calendar Days"] + 1).all()


def test_empty_and_bad_inputs():
    res = run(pd.DataFrame({"s": pd.Series([], dtype=object), "e": pd.Series([], dtype=object)}), end_field="e").raise_for_error()
    assert len(res.output(0)) == 0
    assert run(pd.DataFrame({"s": ["2025-01-01"]})).status == "aborted"  # nothing to do
    out = run(pd.DataFrame({"s": ["garbage", "2025-01-06"], "e": ["2025-01-07", None]}), end_field="e").raise_for_error().output(0)
    assert out["Working Days"].isna().all()


def test_large_input_is_fast():
    n = 500_000
    rng = np.random.default_rng(0)
    s = pd.Timestamp("2015-01-01") + pd.to_timedelta(rng.integers(0, 4000, n), unit="D")
    df = pd.DataFrame({"s": s, "e": s + pd.to_timedelta(rng.integers(0, 60, n), unit="D"), "n": rng.integers(1, 10, n)})
    t0 = time.time()
    out = run(df, end_field="e", days_field="n").raise_for_error().output(0)
    assert time.time() - t0 < 60 and out["Working Days"].notna().all()
