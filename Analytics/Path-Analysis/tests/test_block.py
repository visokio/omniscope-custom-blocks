import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "web-sessions.csv")
EV = pd.DataFrame({"s": ["a", "a", "a", "a", "b", "b", "b", "c", "c", "d"],
                   "e": ["home", "home", "product", "buy", "product", "home", "buy", "home", "product", "help"],
                   "t": ["2025-01-01 10:00:03", "2025-01-01 10:00:01", "2025-01-01 10:00:05", "2025-01-01 10:01:00",
                         "2025-01-01 09:00", "2025-01-01 09:01", "2025-01-01 09:02", "2025-01-01 08:00", "2025-01-01 08:05", "2025-01-01 08:00"]})


def run(df, **opts):
    return run_block(HERE, df, {"path_field": "s", "event_field": "e", "time_field": "t", **opts})


def test_paths_order_collapse_and_counts():
    res = run(EV).raise_for_error()
    p = res.output(0).set_index("Path")
    assert p.loc["home > product > buy", "Paths"] == 1  # a: home, home collapsed
    assert set(p.index) == {"home > product > buy", "product > home > buy", "home > product", "help"}
    assert np.isclose(p["Share"].sum(), 1.0) and p["Cumulative Share"].iloc[-1] == 1.0
    assert np.isclose(p.loc["home > product", "Median Minutes"], 5.0)
    raw = run(EV, collapse_repeats=False).raise_for_error().output(0)
    assert "home > home > product > buy" in set(raw["Path"])


def test_start_end_and_truncation():
    p = run(EV, start_event="product").raise_for_error()
    assert set(p.output(0)["Path"]) == {"product > buy", "product > home > buy", "product"} and "1 paths without" in p.final_message
    e = run(EV, end_events="product").raise_for_error().output(0).set_index("Path")
    assert e.loc["home > product", "Paths"] == 2 and e.loc["home > product", "Reached End Event"] == 2
    t = run(EV, max_steps=2).raise_for_error().output(0)
    assert "home > product > ..." in set(t["Path"]) and t[t["Path"] == "home > product > ..."]["Average Steps (untruncated)"].iloc[0] == 3


def test_transitions_and_markov():
    res = run(EV).raise_for_error()
    tr = res.output(1)
    row = tr[(tr["From"] == "1. home") & (tr["To"] == "2. product")]
    assert row["Paths"].iloc[0] == 2
    assert tr[(tr["From"] == "1. help")]["To"].iloc[0] == "2. (exit)"
    mk = res.output(2)
    assert np.isclose(mk.groupby("From")["Probability"].sum(), 1.0).all()
    hp = mk[(mk["From"] == "home") & (mk["To"] == "product")]["Probability"].iloc[0]
    assert np.isclose(hp, 2 / 3)  # home -> product twice, home -> buy once
    t2 = run(EV, max_steps=1).raise_for_error().output(1)
    assert set(t2["To"]) == {"2. (more)", "2. (exit)"}


def test_no_time_field_uses_input_order():
    p = run_block(HERE, EV, {"path_field": "s", "event_field": "e"}).raise_for_error().output(0)
    assert "home > product > buy" in set(p["Path"]) and "Median Minutes" not in p.columns


def test_sample_sessions():
    res = run_block(HERE, SAMPLE, {"path_field": "Session ID", "event_field": "Page", "time_field": "Event Time", "end_events": "purchase"}).raise_for_error()
    p = res.output(0)
    assert p["Paths"].sum() <= 3000 and "purchase" in res.final_message
    mk = res.output(2)
    assert mk[(mk["From"] == "purchase")].empty  # paths stop at the end event


def test_bad_inputs_and_empty():
    assert run(EV, path_field="zz").status == "aborted"
    assert run(EV, time_field="zz").status == "aborted"
    assert run(EV, max_steps=0).status == "aborted"
    res = run(EV.iloc[0:0]).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0 and len(res.output(2)) == 0
    res = run(EV.assign(e=[None, "", "x", "y", None, None, None, None, None, None])).raise_for_error()
    assert res.output(0)["Path"].tolist() == ["x > y"]


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 400_000
    df = pd.DataFrame({"s": rng.integers(0, 60_000, n), "e": rng.choice(["a", "b", "c", "d", "e", "f"], n),
                       "t": pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 86400 * 7, n), unit="s")})
    t0 = time.time()
    res = run(df, end_events="f").raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == 50
