import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "subscription-contracts.csv")
BASE = {"start_field": "Start Date", "end_field": "End Date"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**BASE, **opts})


def test_monthly_proration_sums_back_to_contract_value():
    res = run(SAMPLE, prorate_fields=["Contract Value"]).raise_for_error()
    out = res.output(0)
    totals = out.groupby("Contract ID")["Contract Value (prorated)"].sum()
    src = pd.read_csv(SAMPLE).set_index("Contract ID")["Contract Value"]
    for cid, total in totals.items():
        assert abs(total - src[cid]) < 1e-3
    s1 = out[out["Contract ID"] == "SUB-001"]
    assert len(s1) == 13 and s1["Days In Period"].iloc[0] == 17 and s1["Days In Range"].iloc[0] == 365
    assert pd.api.types.is_datetime64_any_dtype(out["Period Start"])


def test_end_before_start_goes_to_skipped_output():
    res = run(SAMPLE).raise_for_error()
    sk = res.output(1)
    assert sk["Contract ID"].tolist() == ["SUB-012"]
    assert "before" in sk["Reason"].iloc[0]


def test_missing_end_options():
    df = pd.DataFrame({"Start Date": ["2025-01-30"], "End Date": [None]})
    assert len(run(df, missing_end="START", frequency="DAY").raise_for_error().output(0)) == 1
    assert len(run(df, missing_end="SKIP").raise_for_error().output(1)) == 1
    assert len(run(df, missing_end="TODAY", frequency="YEAR").raise_for_error().output(0)) >= 1


def test_exclusive_end_counts_nights():
    df = pd.DataFrame({"Start Date": ["2025-03-30"], "End Date": ["2025-04-02"], "Price": [300.0]})
    out = run(df, frequency="DAY", inclusive_end=False, prorate_fields=["Price"]).raise_for_error().output(0)
    assert out["Period"].tolist() == ["2025-03-30", "2025-03-31", "2025-04-01"]
    assert np.allclose(out["Price (prorated)"], 100.0)


def test_weeks_quarters_years_labels():
    df = pd.DataFrame({"Start Date": ["2025-03-05"], "End Date": ["2025-07-02"]})
    w = run(df, frequency="WEEK").raise_for_error().output(0)
    assert w["Period"].iloc[0] == "w/c 2025-03-03" and w["Period Start"].iloc[0].dayofweek == 0
    q = run(df, frequency="QUARTER").raise_for_error().output(0)
    assert q["Period"].tolist() == ["2025 Q1", "2025 Q2", "2025 Q3"]
    y = run(df, frequency="YEAR").raise_for_error().output(0)
    assert y["Period"].tolist() == ["2025"]


def test_day_first_text_and_real_dates():
    df = pd.DataFrame({"Start Date": ["03/02/2025"], "End Date": pd.to_datetime(["2025-02-05"])})
    out = run(df, frequency="DAY").raise_for_error().output(0)
    assert out["Period"].tolist() == ["2025-02-03", "2025-02-04", "2025-02-05"]
    out = run(pd.DataFrame({"Start Date": ["02/03/2025"], "End Date": ["02/05/2025"]}), frequency="DAY",
              day_first=False).raise_for_error().output(0)
    assert len(out) == 3


def test_empty_input_keeps_schema():
    df = pd.DataFrame({"Start Date": pd.Series([], dtype=object), "End Date": pd.Series([], dtype=object)})
    res = run(df).raise_for_error()
    assert len(res.output(0)) == 0 and "Days In Period" in res.output(0).columns
    assert len(res.output(1)) == 0 and "Reason" in res.output(1).columns


def test_wrong_types_garbage_dates_and_text_amounts():
    df = pd.DataFrame({"Start Date": ["not a date", "2025-01-01"], "End Date": ["2025-02-01", "2025-01-31"],
                       "Amt": ["abc", "31"]})
    res = run(df, frequency="DAY", prorate_fields=["Amt"]).raise_for_error()
    assert res.output(1)["Reason"].iloc[0].startswith("Start date")
    out = res.output(0)
    assert len(out) == 31 and abs(out["Amt (prorated)"].sum() - 31) < 1e-6


def test_missing_option_aborts():
    res = run_block(HERE, SAMPLE, {"start_field": "Start Date"})
    assert res.status == "aborted"


def test_safety_limit():
    df = pd.DataFrame({"Start Date": ["2000-01-01"], "End Date": ["2025-01-01"]})
    res = run(df, frequency="DAY", max_periods=100).raise_for_error()
    assert len(res.output(0)) == 0 and "More than" in res.output(1)["Reason"].iloc[0]


def test_large_input_is_fast():
    n = 100_000
    start = pd.Timestamp("2024-01-01") + pd.to_timedelta(np.arange(n) % 365, unit="D")
    df = pd.DataFrame({"Start Date": start, "End Date": start + pd.Timedelta(days=730), "V": 1000.0})
    t0 = time.time()
    out = run(df, prorate_fields=["V"]).raise_for_error().output(0)
    assert time.time() - t0 < 60
    assert len(out) > 2_400_000
