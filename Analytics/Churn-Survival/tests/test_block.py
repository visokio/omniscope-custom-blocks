import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "subscriptions.csv")


def run(df, **opts):
    return run_block(HERE, df, opts)


def test_textbook_kaplan_meier():
    # durations 1,2,2,3,4(censored),5 -> S(1)=5/6, S(2)=5/6*3/5=0.5, S(3)=0.5*2/3, S(5)=0
    df = pd.DataFrame({"t": [1, 2, 2, 3, 4, 5], "e": [1, 1, 1, 1, 0, 1]})
    res = run(df, duration_field="t", event_field="e", milestones="2, 3").raise_for_error()
    c = res.output(0).set_index("Time")
    assert np.isclose(c.loc[1.0, "Survival"], 5 / 6) and np.isclose(c.loc[2.0, "Survival"], 0.5) and np.isclose(c.loc[3.0, "Survival"], 1 / 3)
    assert c.loc[4.0, "Censored"] == 1 and c.loc[5.0, "Survival"] == 0 and c.loc[0.0, "At Risk"] == 6
    s = res.output(1).iloc[0]
    assert s["Median Lifetime"] == 2.0 and np.isclose(s["Retention At 3"], 1 / 3) and s["Still Active (censored)"] == 1
    assert np.isclose(s["Restricted Mean Lifetime"], 1 + 5 / 6 + 0.5 + 1 / 3 + 1 / 3)


def test_matches_scipy_km_and_logrank():
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(4)
    n = 400
    g = rng.choice(["a", "b"], n)
    t = rng.exponential(np.where(g == "a", 10, 16))
    cens = rng.uniform(0, 30, n)
    T, E = np.minimum(t, cens), t <= cens
    res = run(pd.DataFrame({"t": T, "e": E, "g": g}), duration_field="t", event_field="e", group_field="g", milestones="5, 10").raise_for_error()
    s = res.output(1).set_index("Group")
    km = stats.ecdf(stats.CensoredData(uncensored=T[(g == "a") & E], right=T[(g == "a") & ~E])).sf
    assert np.isclose(s.loc["a", "Retention At 5"], km.evaluate(5.0)) and np.isclose(s.loc["a", "Retention At 10"], km.evaluate(10.0))
    lr = stats.logrank(stats.CensoredData(uncensored=T[(g == "a") & E], right=T[(g == "a") & ~E]),
                       stats.CensoredData(uncensored=T[(g == "b") & E], right=T[(g == "b") & ~E]))
    tst = res.output(2).iloc[0]
    assert np.isclose(tst["Chi-Square"], lr.statistic ** 2, rtol=1e-6) and np.isclose(tst["P Value"], lr.pvalue, rtol=1e-4)
    assert s.loc["a", "Vs Rest"] == "Shorter lifetimes" and s.loc["b", "Vs Rest"] == "Longer lifetimes"


def test_dates_censoring_and_as_of():
    df = pd.DataFrame({"s": ["2025-01-01", "2025-01-01", "2025-01-01", "2025-03-01"], "e": ["2025-01-31", None, "2025-12-31", None]})
    res = run(df, start_field="s", end_field="e", unit="DAY", as_of="2025-06-30").raise_for_error()
    s = res.output(1).iloc[0]
    assert s["Ended"] == 1 and s["Still Active (censored)"] == 3  # the end after the as-of date is censored
    c = res.output(0)
    assert c["Time"].max() == 180  # 1 Jan to 30 Jun
    kind = pd.DataFrame({"s": ["2025-01-01"] * 2, "e": ["2025-02-01"] * 2, "why": ["Cancelled", "Upgraded"]})
    s2 = run(kind, start_field="s", end_field="e", event_field="why").raise_for_error().output(1).iloc[0]
    assert s2["Ended"] == 1  # only the cancellation counts


def test_sample_subscriptions():
    res = run_block(HERE, SAMPLE, {"start_field": "Start Date", "end_field": "End Date", "group_field": "Plan"}).raise_for_error()
    s = res.output(1).set_index("Group")
    assert s.loc["Annual", "Vs Rest"] == "Longer lifetimes" and s.loc["Monthly (promo)", "Retention At 6"] < s.loc["Monthly", "Retention At 6"]
    assert res.output(2).iloc[0]["Significant"] == "Yes" and s["Customers"].sum() == 2400


def test_bad_inputs_and_empty():
    df = pd.DataFrame({"t": [1.0, 2.0], "e": [1, 0]})
    assert run(df).status == "aborted"
    assert run(df, duration_field="zz").status == "aborted"
    assert run(df, duration_field="t", milestones="a, b").status == "aborted"
    assert run(df, duration_field="t", confidence=2).status == "aborted"
    res = run(df.iloc[0:0], duration_field="t").raise_for_error()
    assert res.output(1).iloc[0]["Customers"] == 0
    res = run(pd.DataFrame({"t": ["x", -1, 3]}), duration_field="t").raise_for_error()
    assert res.output(1).iloc[0]["Customers"] == 1 and "skipped" in res.final_message


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 200_000
    df = pd.DataFrame({"t": np.round(rng.exponential(12, n), 1), "e": rng.random(n) < 0.7, "g": rng.choice(list("abcdef"), n)})
    t0 = time.time()
    res = run(df, duration_field="t", event_field="e", group_field="g").raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(1)) == 6
