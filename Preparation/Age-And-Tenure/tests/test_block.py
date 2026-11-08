import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "employees.csv")


def run(df, **opts):
    return run_block(HERE, df, {"start_field": "s", **opts})


def test_exact_age_and_leap_day():
    df = pd.DataFrame({"s": ["1990-03-15", "1980-02-29", "2000-11-05", "2025-12-01"]})
    o = run(df, as_of="2025-11-05").raise_for_error().output(0)
    assert (o["Years"].iloc[0], o["Months"].iloc[0], o["Days"].iloc[0]) == (35, 7, 21)
    assert o["Next Anniversary"].iloc[1].strftime("%Y-%m-%d") == "2026-02-28" and o["Years"].iloc[1] == 45
    assert o["Years"].iloc[2] == 25 and o["Days To Next Anniversary"].iloc[2] == 365 and pd.isna(o["Years"].iloc[3])
    assert o["Band"].tolist()[:3] == ["35-44", "45-54", "25-34"]


def test_end_date_milestones_and_bands_output():
    df = pd.DataFrame({"s": ["2015-12-01", "2010-01-01"], "e": [None, "2020-06-30"]})
    res = run(df, end_field="e", as_of="2025-11-05", bands="5, 10", milestones="10").raise_for_error()
    o = res.output(0)
    assert o["Upcoming Milestone"].iloc[0] == "10 years on 2015-12-01".replace("2015", "2025") and o["Years"].iloc[1] == 10
    b = res.output(1)
    assert set(b["Band"]) == {"5-9", "10+"} and b["Rows"].sum() == 2


def test_sample_and_bad_inputs():
    res = run_block(HERE, SAMPLE, {"start_field": "Date Of Birth", "as_of": "2025-11-05"}).raise_for_error()
    assert res.output(0)["Years"].notna().sum() == 300
    assert run(pd.DataFrame({"s": ["2000-01-01"]}), bands="a, b").status == "aborted"
    assert run(pd.DataFrame({"s": ["2000-01-01"]}), as_of="soon").status == "aborted"
    big = pd.DataFrame({"s": (pd.Timestamp("1950-01-01") + pd.to_timedelta(np.random.default_rng(0).integers(0, 25000, 100_000), unit="D")).strftime("%Y-%m-%d")})
    t0 = time.time()
    run(big, as_of="2025-11-05").raise_for_error()
    assert time.time() - t0 < 120


def test_leavers_get_no_upcoming_milestone():
    # Left in 2020 with 10 years falling 3 days after leaving: before the fix this showed "10 years on 2020-06-28".
    df = pd.DataFrame({"s": ["2010-06-28", "2015-12-01", "2015-12-01", "2015-12-01"],
                       "e": ["2020-06-25", None, "2026-06-30", "2025-11-20"]})
    o = run(df, end_field="e", as_of="2025-11-05", milestones="10").raise_for_error().output(0)
    assert [x if isinstance(x, str) else None for x in o["Upcoming Milestone"]] == [
        None, "10 years on 2025-12-01", "10 years on 2025-12-01", None]
    assert o["Years"].iloc[0] == 9  # still measured to the leaving date


def test_single_year_band_label():
    df = pd.DataFrame({"s": ["2024-06-01", "2023-06-01", "2021-06-01", "2025-06-01"]})
    res = run(df, as_of="2025-11-05", bands="1, 2, 5").raise_for_error()
    assert res.output(0)["Band"].tolist() == ["1", "2-4", "2-4", "Under 1"]
    assert res.output(1)["Band"].tolist() == ["Under 1", "1", "2-4"]
