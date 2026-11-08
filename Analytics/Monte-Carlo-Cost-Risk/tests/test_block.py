import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "project-estimate.csv")
O = {"name_field": "n", "low_field": "lo", "likely_field": "ml", "high_field": "hi"}
DF = pd.DataFrame({"n": ["a", "b", "c"], "lo": [80.0, 40.0, 10.0], "ml": [100.0, 50.0, 20.0], "hi": [160.0, 90.0, 60.0], "g": ["x", "x", "y"]})


def run(df, **opts):
    return run_block(HERE, df, {**O, **opts})


def test_pert_triangular_uniform_means_and_repeatable():
    s = run(DF, iterations=50000).raise_for_error().output(0).iloc[0]
    pert_mean = sum((l + 4 * m + h) / 6 for l, m, h in zip(DF.lo, DF.ml, DF.hi))
    assert abs(s["Mean"] - pert_mean) < 0.5 and s["Base Estimate (most likely)"] == 170
    assert s["P10"] < s["P50"] < s["P80"] < s["P90"] < s["P95"]
    assert np.isclose(s["Contingency To P80"], s["P80"] - 170)
    t = run(DF, iterations=50000, distribution="TRIANGULAR").raise_for_error().output(0).iloc[0]
    assert abs(t["Mean"] - sum((l + m + h) / 3 for l, m, h in zip(DF.lo, DF.ml, DF.hi))) < 0.5
    u = run(DF, iterations=50000, distribution="UNIFORM").raise_for_error().output(0).iloc[0]
    assert abs(u["Mean"] - sum((l + h) / 2 for l, h in zip(DF.lo, DF.hi))) < 0.6
    a = run(DF, seed=7).raise_for_error().output(0)
    b = run(DF, seed=7).raise_for_error().output(0)
    assert a.equals(b)


def test_risk_events_and_groups():
    df = DF.assign(p=[None, None, 0.25])
    res = run(df, iterations=40000, probability_field="p", group_field="g").raise_for_error()
    s = res.output(0).set_index("Scope")
    assert s.loc["Total", "Base Estimate (most likely)"] == 150 and np.isclose(s.loc["Total", "Expected Risk Events"], 5.0)
    assert abs(s.loc["y", "Mean"] - 0.25 * (10 + 80 + 60) / 6) < 0.4 and s.loc["y", "P50"] == 0
    assert set(s.index) == {"Total", "x", "y"}
    pct = run(df.assign(p=[None, None, 25]), iterations=40000, probability_field="p").raise_for_error().output(0).iloc[0]
    assert abs(pct["Mean"] - s.loc["Total", "Mean"]) < 1.0  # 25 read as 25%


def test_correlation_widens_spread_and_drivers():
    many = pd.DataFrame({"n": [f"l{i}" for i in range(20)], "lo": 90.0, "ml": 100.0, "hi": 130.0})
    sd0 = run(many).raise_for_error().output(0).iloc[0]["Std Dev"]
    sd5 = run(many, correlation=0.5).raise_for_error().output(0).iloc[0]["Std Dev"]
    assert sd5 > 2 * sd0
    d = run(DF).raise_for_error().output(1)
    assert d.iloc[0]["n"] == "a" and d["Driver Rank"].tolist() == [1, 2, 3] and np.isclose(d["Share Of Variance"].sum(), 1.0, atol=0.03)
    c = run(DF, target=200).raise_for_error().output(0).iloc[0]
    assert 0 < c["Probability Over Target"] < 1 and np.isclose(c["Probability Over Target"] + c["Confidence Level Of Target"], 1)
    curve = run(DF, bins=20).raise_for_error().output(2)
    assert len(curve) == 20 and np.isclose(curve["Cumulative Probability"].iloc[-1], 1.0)


def test_sample_estimate():
    res = run_block(HERE, SAMPLE, {"name_field": "Line Item", "low_field": "Low (GBP k)", "likely_field": "Most Likely (GBP k)", "high_field": "High (GBP k)",
                                   "probability_field": "Probability", "group_field": "Package", "correlation": 0.4, "target": 5900}).raise_for_error()
    s = res.output(0).set_index("Scope")
    assert s.loc["Total", "Base Estimate (most likely)"] == 5385 and s.loc["Total", "P80"] > 5385
    assert len(res.output(1)) == 20


def test_bad_inputs_and_edge_cases():
    assert run(DF.assign(lo=[120.0, 40.0, 10.0])).status == "aborted"  # low above most likely
    assert run(DF, low_field="zz").status == "aborted"
    assert run(DF, iterations=10).status == "aborted"
    assert run(DF, correlation=1.0).status == "aborted"
    assert run(DF.assign(ml=["x", "y", "z"], lo=None, hi=None)).status == "aborted"
    fixed = run(DF.assign(lo=DF.ml, hi=DF.ml)).raise_for_error().output(0).iloc[0]
    assert fixed["Std Dev"] == 0 and fixed["P90"] == 170
    res = run(DF.assign(lo=None, hi=None)).raise_for_error()  # missing low / high fall back to most likely
    assert res.output(0).iloc[0]["P95"] == 170


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 1000
    ml = rng.gamma(2, 50, n)
    df = pd.DataFrame({"n": [f"l{i}" for i in range(n)], "lo": ml * 0.9, "ml": ml, "hi": ml * 1.4})
    t0 = time.time()
    res = run(df, iterations=10000, correlation=0.3).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(1)) == n
