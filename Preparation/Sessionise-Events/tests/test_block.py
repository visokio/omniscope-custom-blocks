import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "web-clickstream.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"user_field": "u", "time_field": "t", **opts})


def events():
    return pd.DataFrame({"u": ["a", "a", "a", "b", "a", "b"],
                         "t": ["2025-01-01 10:00:00", "2025-01-01 10:10:00", "2025-01-01 11:00:00",
                               "2025-01-01 09:00:00", "2025-01-01 10:05:00", "2025-01-01 09:20:00"],
                         "p": ["/home", "/basket", "/home", "/blog", "/product", "/home"], "v": [0.0, 0.0, 12.5, 0.0, 0.0, 0.0]})


def test_sessions_by_gap_out_of_order_input():
    res = run(events(), event_field="p", value_field="v").raise_for_error()
    ev = res.output(0)
    assert ev["Session ID"].tolist() == ["a-1", "a-1", "a-2", "b-1", "a-1", "b-1"]
    assert ev["Event Number In Session"].tolist() == [1, 3, 1, 1, 2, 2]
    assert ev["Is Session Start"].tolist() == ["Yes", "No", "Yes", "Yes", "No", "No"]
    assert ev["Seconds Since Previous Event"].tolist()[1] == 300.0
    s = res.output(1).set_index("Session ID")
    assert s.loc["a-1", "Events"] == 3 and s.loc["a-1", "Duration (seconds)"] == 600.0
    assert s.loc["a-1", "First Event"] == "/home" and s.loc["a-1", "Last Event"] == "/basket"
    assert s.loc["a-2", "Bounce"] == "Yes" and s.loc["a-2", "Total Value"] == 12.5


def test_gap_option_and_max_length():
    assert len(run(events(), gap_minutes=60).raise_for_error().output(1)) == 2
    ev = pd.DataFrame({"u": ["x"] * 5, "t": pd.date_range("2025-01-01", periods=5, freq="20min")})
    s = run(ev, max_session_hours=0.5).raise_for_error().output(1)
    assert len(s) == 3 and s["Events"].tolist() == [2, 2, 1]


def test_timezone_aware_timestamps_survive():
    ev = pd.DataFrame({"u": ["x", "x"], "t": pd.to_datetime(["2025-06-01 10:00", "2025-06-01 12:00"]).tz_localize("UTC")})
    s = run(ev).raise_for_error().output(1)
    assert len(s) == 2 and str(s["Session Start"].dt.tz) == "UTC"


def test_sample_clickstream():
    res = run_block(HERE, SAMPLE, {"user_field": "Visitor", "time_field": "Timestamp", "event_field": "Page", "value_field": "Order Value"}).raise_for_error()
    ev, s = res.output(0), res.output(1)
    assert ev["Session ID"].notna().all() and s["Events"].sum() == len(ev)
    assert s["Visitor"].nunique() == 250 and (s["Duration (seconds)"] >= 0).all()


def test_bad_rows_and_empty():
    df = events()
    df.loc[len(df)] = [None, "2025-01-01 10:00:00", "/x", 0.0]
    df.loc[len(df)] = ["a", "never", "/x", 0.0]
    res = run(df).raise_for_error()
    assert res.output(0)["Session ID"].isna().sum() == 2 and "2 events without" in res.final_message
    empty = pd.DataFrame({"u": pd.Series([], dtype=object), "t": pd.Series([], dtype=object)})
    res = run(empty).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0


def test_bad_options():
    assert run(events(), gap_minutes=0).status == "aborted"
    assert run(events(), event_field="nope").status == "aborted"
    assert run_block(HERE, events(), {"user_field": "u"}).status == "aborted"


def test_large_input_is_fast():
    n = 1_000_000
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"u": rng.integers(0, 20_000, n), "t": pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 86400 * 30, n), unit="s")})
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 90 and res.output(1)["Events"].sum() == n
