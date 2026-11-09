import math
import os

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "test-plans.csv")


def run(df=None, **opts):
    return run_block(HERE, df, opts)


def one(**opts):
    return run(**opts).raise_for_error().output(0).iloc[0]


def test_two_means_formula():
    r = one(test_type="MEAN", baseline=46.5, effect=2, relative_effect=False, sd=38)
    expect = 2 * (1.959963985 + 0.841621234) ** 2 * 38 ** 2 / 4
    assert r["Sample Size Group 1"] == math.ceil(expect) and r["Total Sample Size"] == 2 * math.ceil(expect)


def test_proportions_survey_and_population():
    r = one(baseline=0.10, effect=0.2)  # 10% -> 12%
    p1, p2 = 0.10, 0.12
    pbar = 0.11
    za, zb = 1.959963985, 0.841621234
    n = (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2 / 0.02 ** 2
    assert r["Sample Size Group 1"] == math.ceil(n) and np.isclose(r["Target"], 0.12)
    s = one(test_type="SURVEY", baseline=0.5, margin=0.03)
    assert s["Total Sample Size"] == math.ceil(1.959963985 ** 2 * 0.25 / 0.0009)
    f = one(test_type="SURVEY", baseline=0.5, margin=0.05, population=1200)
    n0 = 1.959963985 ** 2 * 0.25 / 0.0025
    assert f["Total Sample Size"] == math.ceil(n0 / (1 + (n0 - 1) / 1200))


def test_options_change_sizes_in_the_right_direction():
    base = one(baseline=0.05, effect=0.1)["Total Sample Size"]
    assert one(baseline=0.05, effect=0.2)["Total Sample Size"] < base
    assert one(baseline=0.05, effect=0.1, power=0.9)["Total Sample Size"] > base
    assert one(baseline=0.05, effect=0.1, sides="1")["Total Sample Size"] < base
    un = one(baseline=0.05, effect=0.1, ratio=2.0)
    assert abs(un["Sample Size Group 2"] - 2 * un["Sample Size Group 1"]) <= 2 and un["Total Sample Size"] > base
    d = one(baseline=0.05, effect=0.1, daily_traffic=1000)
    assert d["Days Needed"] == math.ceil(d["Total Sample Size"] / 1000)


def test_scenarios_input_and_power_curve():
    res = run(SAMPLE).raise_for_error()
    s = res.output(0).set_index("Scenario")
    assert len(s) == 6 and s.loc["Checkout redesign (5% lift)", "Total Sample Size"] > 3.5 * s.loc["Checkout redesign (10% lift)", "Total Sample Size"]
    c = res.output(1)
    one_curve = c[c["Scenario"] == "Email subject line"]
    assert one_curve["Power"].is_monotonic_increasing and abs(one_curve[np.isclose(one_curve["Share Of Required"], 1.0)]["Power"].iloc[0] - 0.8) < 0.01
    assert set(c["Scenario"]) == set(s.index[s["Type"] != "SURVEY"])


def test_bad_inputs():
    assert run(baseline=0.95, effect=0.1).status == "aborted"  # target rate above 1
    assert run(alpha=0.7).status == "aborted"
    assert run(test_type="MEAN", effect=0, relative_effect=False).status == "aborted"
    assert run(pd.DataFrame({"Scenario": ["x"], "Type": ["weird"]})).status == "aborted"
    assert run(pd.DataFrame({"Scenario": ["x"], "Baseline": ["abc"]})).status == "aborted"
    assert run(pd.DataFrame({"Scenario": ["x"], "Baseline": ["4%"], "Effect": ["25%"]})).raise_for_error().output(0).iloc[0]["Target"] == 0.05
