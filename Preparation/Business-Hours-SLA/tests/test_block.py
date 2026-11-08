import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "tickets.csv")


def run(df, **opts):
    return run_block(HERE, df, {"start_field": "s", "end_field": "e", **opts})


def one(s, e, **opts):
    return run(pd.DataFrame({"s": [s], "e": [e]}), **opts).raise_for_error().output(0).iloc[0]


def test_business_hours_cases():
    assert np.isclose(one("2025-11-03 10:00", "2025-11-03 12:30")["Business Hours Elapsed"], 2.5)
    assert np.isclose(one("2025-11-03 07:00", "2025-11-03 20:00")["Business Hours Elapsed"], 8.5)          # outside hours ignored
    assert np.isclose(one("2025-11-07 16:30", "2025-11-10 10:00")["Business Hours Elapsed"], 2.0)          # Friday to Monday
    assert np.isclose(one("2025-11-08 10:00", "2025-11-09 15:00")["Business Hours Elapsed"], 0.0)          # weekend
    assert np.isclose(one("2025-12-24 16:00", "2025-12-29 10:00")["Business Hours Elapsed"], 1.5 + 1.0)   # Christmas and Boxing Day
    assert np.isclose(one("2025-12-24 16:00", "2025-12-29 10:00", region="NONE")["Business Hours Elapsed"], 1.5 + 8.5 + 8.5 + 1.0)
    assert np.isclose(one("2025-11-03 09:00", "2025-11-03 17:00", open_time="08:00", close_time="16:00")["Business Hours Elapsed"], 7.0)


def test_sla_due_and_status():
    r = one("2025-11-07 16:00", "2025-11-10 11:00", sla_hours=2)
    assert r["SLA Due"].strftime("%Y-%m-%d %H:%M") == "2025-11-10 09:30" and r["SLA Status"] == "Breached" and np.isclose(r["Business Hours To Spare"], -1.5)
    df = pd.DataFrame({"s": ["2025-11-03 09:00", "2025-11-03 09:00", "2025-11-03 09:00"], "e": ["2025-11-03 10:00", None, None], "p": ["P1", "P2", "P3"]})
    o = run(df, priority_field="p", sla_by_priority="P1=4, P2=8, P3=100", as_of="2025-11-04 12:00").raise_for_error().output(0)
    assert o["SLA Status"].tolist() == ["Met", "Open and breached", "Open"] and o["Open"].tolist() == ["No", "Yes", "Yes"]


def test_custom_holidays_weekend_and_bad_input():
    assert np.isclose(one("2025-11-03 09:00", "2025-11-04 17:30", custom_holidays="2025-11-04")["Business Hours Elapsed"], 8.5)
    assert np.isclose(one("2025-11-08 09:00", "2025-11-08 17:30", weekend="NONE", region="NONE")["Business Hours Elapsed"], 8.5)
    assert run(pd.DataFrame({"s": ["x"], "e": ["y"]}), open_time="18:00", close_time="09:00").status == "aborted"
    assert run(pd.DataFrame({"s": ["x"], "e": ["y"]}), sla_by_priority="P1 is four").status == "aborted"
    assert pd.isna(one("2025-11-05 10:00", "2025-11-03 10:00")["Business Hours Elapsed"])  # end before start


def test_sample_and_large():
    res = run_block(HERE, SAMPLE, {"start_field": "Opened", "end_field": "Resolved", "priority_field": "Priority", "sla_by_priority": "P1=4, P2=8, P3=24, P4=40",
                                   "as_of": "2025-11-28 17:00"}).raise_for_error()
    s = res.output(1).set_index("Priority")
    assert s.loc["All", "Items"] == 600 and s.loc["P1", "Met Rate (closed)"] < s.loc["P4", "Met Rate (closed)"]
    rng = np.random.default_rng(0)
    st = pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 300 * 24 * 60, 100_000), unit="m")
    big = pd.DataFrame({"s": st, "e": st + pd.to_timedelta(rng.integers(10, 5000, 100_000), unit="m")})
    t0 = time.time()
    run(big, sla_hours=8).raise_for_error()
    assert time.time() - t0 < 120
