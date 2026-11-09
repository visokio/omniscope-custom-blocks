import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "daily-sales.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"date_field": "d", "value_field": "v", **opts})


def monthly(start="2023-01", n=34, g=None):
    ms = pd.period_range(start, periods=n, freq="M")
    df = pd.DataFrame({"d": [p.end_time.strftime("%Y-%m-%d") for p in ms], "v": np.arange(1, n + 1, dtype=float) * 10.5})
    if g:
        df["g"] = g
    return df


def test_calendar_year_windows():
    # values 10.5 * month number; Jan 2023 = 1 ... Oct 2025 = 34
    s = run(monthly()).raise_for_error().output(0).iloc[0]
    k = 10.5
    assert s["Reporting Month"] == "2025-10" and s["Month"] == 34 * k and s["Prior Month"] == 33 * k and s["Same Month Last Year"] == 22 * k
    assert s["YTD"] == sum(range(25, 35)) * k and s["Prior YTD"] == sum(range(13, 23)) * k
    assert s["MAT"] == sum(range(23, 35)) * k and s["Prior MAT"] == sum(range(11, 23)) * k
    assert s["QTD"] == (34) * k  # Q4 starts in October
    assert np.isclose(s["% Change vs Last Year"], 34 / 22 - 1)


def test_fiscal_year_april():
    s = run(monthly(), fiscal_year_start=4).raise_for_error()
    r = s.output(0).iloc[0]
    assert r["Fiscal Year Start"] == "2025-04" and r["YTD"] == sum(range(28, 35)) * 10.5
    assert r["QTD"] == (34) * 10.5  # fiscal Q3 starts in October
    t = s.output(1)
    assert t[t.Month == "2025-03"]["Fiscal Year"].iloc[0] == "FY 2024/25" and t[t.Month == "2025-04"]["YTD"].iloc[0] == 28 * 10.5


def test_partial_month_and_as_of():
    df = pd.concat([monthly(), pd.DataFrame({"d": ["2025-11-03"], "v": [5.0]})])
    assert run(df).raise_for_error().output(0).iloc[0]["Reporting Month"] == "2025-10"
    assert run(df, complete_months_only=False).raise_for_error().output(0).iloc[0]["Reporting Month"] == "2025-11"
    assert run(df, as_of="2025-06-15").raise_for_error().output(0).iloc[0]["Month"] == 30 * 10.5
    assert run(df, as_of="soon").status == "aborted"


def test_groups_total_and_trend():
    df = pd.concat([monthly(g="a"), monthly(g="b")])
    res = run(df, group_fields=["g"]).raise_for_error()
    s = res.output(0).set_index("g")
    assert s.loc["Total", "YTD"] == 2 * s.loc["a", "YTD"]
    t = res.output(1)
    assert len(t) == 2 * 34 and np.isnan(t[t.g == "a"]["MAT"].iloc[10]) and t[t.g == "a"]["MAT"].iloc[11] == sum(range(1, 13)) * 10.5


def test_sample_daily():
    res = run_block(HERE, SAMPLE, {"date_field": "Date", "value_field": "Sales", "group_fields": ["Region"], "fiscal_year_start": 4}).raise_for_error()
    s = res.output(0).set_index("Region")
    assert s.loc["Total", "Reporting Month"] == "2025-10" and s.loc["South", "% Change MAT vs Prior MAT"] > s.loc["Scotland", "% Change MAT vs Prior MAT"]


def test_bad_and_empty():
    assert run(monthly(), value_field="nope").status == "aborted"
    assert run(monthly(), fiscal_year_start=13).status == "aborted"
    assert run(pd.DataFrame({"d": ["x"], "v": [1.0]})).status == "aborted"


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 1_000_000
    df = pd.DataFrame({"d": pd.Timestamp("2022-01-01") + pd.to_timedelta(rng.integers(0, 1400, n), unit="D"),
                       "v": rng.gamma(2, 10, n), "g": rng.integers(0, 300, n)})
    t0 = time.time()
    res = run(df, group_fields=["g"]).raise_for_error()
    assert time.time() - t0 < 90 and len(res.output(0)) == 301
