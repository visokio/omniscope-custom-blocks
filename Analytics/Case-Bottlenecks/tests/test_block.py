import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "claims-events.csv")
EV = pd.DataFrame({"c": ["1", "1", "1", "1", "2", "2"], "a": ["open", "check", "check", "close", "open", "close"],
                   "t": ["2025-01-01 10:00", "2025-01-01 12:00", "2025-01-01 18:00", "2025-01-02 10:00", "2025-01-03 09:00", "2025-01-03 10:00"]})


def run(df, **opts):
    return run_block(HERE, df, {"case_field": "c", "activity_field": "a", "time_field": "t", **opts})


def test_cases_and_rework():
    res = run(EV.sample(frac=1, random_state=3)).raise_for_error()  # input order does not matter
    c = res.output(0).set_index("c")
    assert c.loc["1", "Duration (Hours)"] == 24.0 and c.loc["1", "Steps"] == 4 and c.loc["1", "Rework Steps"] == 1
    assert c.loc["1", "Route"] == "open > check > check > close" and c.loc["2", "Duration (Hours)"] == 1.0
    d = run(EV, unit="DAYS").raise_for_error().output(0).set_index("c")
    assert d.loc["1", "Duration (Days)"] == 1.0


def test_handovers_and_activities():
    res = run(EV).raise_for_error()
    h = res.output(1).set_index(["From Activity", "To Activity"])
    assert h.loc[("check", "close"), "Median Hours"] == 16.0 and h.loc[("check", "check"), "Repeat Of Same Activity"] == "Yes"
    assert h.loc[("open", "close"), "Handovers"] == 1 and np.isclose(h["Share Of All Waiting"].sum(), 1.0)
    assert res.output(1).iloc[0]["From Activity"] == "check" and res.output(1).iloc[0]["To Activity"] == "close"  # largest total first
    a = res.output(2).set_index("Activity")
    assert a.loc["check", "Rework Occurrences"] == 1 and a.loc["close", "Times Last Step"] == 2


def test_sample_and_bad_inputs():
    res = run_block(HERE, SAMPLE, {"case_field": "Claim ID", "activity_field": "Activity", "time_field": "Timestamp"}).raise_for_error()
    h = res.output(1)
    assert (h.iloc[0]["From Activity"], h.iloc[0]["To Activity"]) == ("Documents requested", "Documents received")
    assert len(res.output(0)) == 900
    assert run(EV, case_field="zz").status == "aborted"
    r = run(EV.assign(t=["x"] + EV["t"].tolist()[1:])).raise_for_error()
    assert "skipped" in r.final_message and r.output(0).set_index("c").loc["1", "Steps"] == 3
    assert len(run(EV.iloc[0:0]).raise_for_error().output(0)) == 0


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 300_000
    df = pd.DataFrame({"c": rng.integers(0, 40_000, n).astype(str), "a": rng.choice(list("ABCDEF"), n),
                       "t": pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 10**7, n), unit="s")})
    t0 = time.time()
    run(df).raise_for_error()
    assert time.time() - t0 < 120
