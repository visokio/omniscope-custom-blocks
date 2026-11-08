import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "web-events.csv")
F = {"user_field": "u", "event_field": "e", "time_field": "t", "steps": "a, b, c"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**F, **opts})


def ev(rows):
    return pd.DataFrame(rows, columns=["u", "e", "t", "seg"])


DATA = ev([("1", "a", "2025-01-01 10:00", "x"), ("1", "b", "2025-01-01 10:05", "x"), ("1", "c", "2025-01-01 11:00", "x"),
           ("2", "a", "2025-01-01 10:00", "y"), ("2", "B", "2025-01-01 10:30", "y"),
           ("3", "b", "2025-01-01 09:00", "x"), ("3", "a", "2025-01-01 10:00", "x"), ("3", "c", "2025-01-03 10:00", "x"),
           ("4", "noise", "2025-01-01 10:00", "y")])


def test_ordered_funnel_counts():
    res = run(DATA).raise_for_error()
    f = res.output(0).set_index("Step")
    assert f["Users"].tolist() == [3, 2, 1]  # user 3's b happened before a, so it does not count in order
    assert np.isclose(f.loc["b", "Conversion From Start"], 2 / 3) and np.isclose(f.loc["c", "Conversion From Previous"], 0.5)
    assert f.loc["b", "Drop-off From Previous"] == 1 and np.isclose(f.loc["b", "Median Hours From Previous"], (5 / 60 + 0.5) / 2)
    u = res.output(1).set_index("u")
    assert u.loc["1", "Converted"] == "Yes" and u.loc["2", "Furthest Step"] == "b" and u.loc["3", "Furthest Step"] == "a"
    assert "noise" in res.final_message


def test_unordered_and_window():
    assert run(DATA, ordered=False).raise_for_error().output(0)["Users"].tolist() == [3, 3, 2]
    assert run(DATA, ordered=False, window_hours=24).raise_for_error().output(0)["Users"].tolist() == [3, 3, 1]


def test_segments():
    f = run(DATA, segment_fields=["seg"]).raise_for_error().output(0)
    x = f[f.seg == "x"]["Users"].tolist()
    assert x == [2, 1, 1] and f[f.seg == "y"]["Users"].tolist() == [1, 1, 0]


def test_sample_events():
    res = run_block(HERE, SAMPLE, {"user_field": "User ID", "event_field": "Event", "time_field": "Event Time",
                                   "steps": "view_product, add_to_basket, begin_checkout, purchase", "segment_fields": ["Device"]}).raise_for_error()
    f = res.output(0)
    d = f[f.Device == "Desktop"].set_index("Step")["Conversion From Start"]
    m = f[f.Device == "Mobile"].set_index("Step")["Conversion From Start"]
    assert d["purchase"] > m["purchase"]
    assert len(res.output(1)) == 2500


def test_bad_inputs_and_empty():
    assert run(DATA, steps="only_one").status == "aborted"
    assert run(DATA, user_field="nope").status == "aborted"
    res = run(DATA.iloc[0:0]).raise_for_error()
    assert res.output(0)["Users"].sum() == 0 and len(res.output(1)) == 0


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 300_000
    users = rng.integers(0, 100_000, n)
    df = pd.DataFrame({"u": users, "e": rng.choice(["a", "b", "c", "x"], n),
                       "t": pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 86400 * 30, n), unit="s")})
    t0 = time.time()
    res = run(df, window_hours=72).raise_for_error()
    assert time.time() - t0 < 120 and res.output(0)["Users"].is_monotonic_decreasing
