import math
import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "nps-survey.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"score_field": "s", **opts})


def test_basic_nps_and_error():
    # 5 promoters, 3 passives, 2 detractors -> NPS 30
    df = pd.DataFrame({"s": [10, 9, 9, 10, 9, 7, 8, 7, 3, 6]})
    res = run(df).raise_for_error()
    r = res.output(0).iloc[0]
    assert r["Promoters"] == 5 and r["Passives"] == 3 and r["Detractors"] == 2
    assert math.isclose(r["NPS"], 30.0)
    se = 100 * math.sqrt((0.5 + 0.2 - 0.3 ** 2) / 10)
    assert math.isclose(r["Standard Error"], se) and math.isclose(r["Margin Of Error"], 1.959963985 * se, rel_tol=1e-6)
    assert r["Small Sample"] == "Yes"
    pts = res.output(2)["NPS Points"]
    assert math.isclose(pts.mean(), 30.0) and res.output(2)["NPS Category"].iloc[8] == "Detractor"
    d = res.output(1)
    assert len(d) == 11 and math.isclose(d["Share"].sum(), 1.0)


def test_invalid_scores_skipped():
    df = pd.DataFrame({"s": ["10", "9", "Don't know", None, "11", "7.5", "0"]})
    res = run(df).raise_for_error()
    r = res.output(0).iloc[0]
    assert r["Responses"] == 3 and math.isclose(r["NPS"], 100 * (2 - 1) / 3)
    assert "1 blank" in res.final_message and "3 not a whole number" in res.final_message


def test_weights_and_effective_n():
    df = pd.DataFrame({"s": [10, 0, 0], "w": [2.0, 1.0, 1.0]})
    r = run(df, weight_field="w").raise_for_error().output(0).iloc[0]
    assert math.isclose(r["NPS"], 0.0) and math.isclose(r["Effective Sample Size"], 16 / 6)


def test_groups_vs_rest_and_periods():
    df = pd.DataFrame({"s": [10] * 200 + [0] * 200, "g": ["a"] * 200 + ["b"] * 200,
                       "d": ["2025-01-15"] * 100 + ["2025-04-15"] * 100 + ["2025-01-15"] * 100 + ["2025-04-15"] * 100})
    s = run(df, group_fields=["g"]).raise_for_error().output(0).set_index("g")
    assert s.loc["All", "NPS"] == 0 and s.loc["a", "Vs Rest"] == "Higher" and s.loc["b", "Vs Rest"] == "Lower"
    df2 = pd.DataFrame({"s": [10] * 50 + [9] * 50 + [0] * 50 + [10] * 50, "d": ["2025-01-10"] * 100 + ["2025-02-10"] * 100})
    p = run(df2, date_field="d", period="MONTH").raise_for_error().output(0)
    assert p["Period"].tolist() == ["2025-01", "2025-02"] and math.isclose(p["Change Vs Previous"].iloc[1], -100.0)
    assert p["Change Significant"].iloc[1] == "Lower"


def test_sample_survey():
    res = run_block(HERE, SAMPLE, {"score_field": "Likelihood To Recommend", "group_fields": ["Channel"]}).raise_for_error()
    s = res.output(0).set_index("Channel")
    assert s.loc["Contact Centre", "Vs Rest"] == "Lower" and s.loc["Online", "Vs Rest"] == "Higher"
    assert s.loc["All", "Responses"] == 3160


def test_bad_inputs_and_empty():
    assert run(pd.DataFrame({"x": [1]})).status == "aborted"
    assert run(pd.DataFrame({"s": [1]}), period="MONTH").status == "aborted"
    assert run(pd.DataFrame({"s": [1]}), confidence=1.5).status == "aborted"
    res = run(pd.DataFrame({"s": pd.Series([], dtype="float64"), "g": pd.Series([], dtype=object)}), group_fields=["g"]).raise_for_error()
    assert res.output(0)["Responses"].sum() == 0
    res = run(pd.DataFrame({"s": ["n/a", "x"]})).raise_for_error()
    assert res.output(0)["Responses"].iloc[0] == 0


def test_large_input_is_fast():
    rng = np.random.default_rng(1)
    n = 500_000
    df = pd.DataFrame({"s": rng.integers(0, 11, n), "g": rng.choice(list("abcdefghij"), n),
                       "d": pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 730, n), unit="D")})
    t0 = time.time()
    res = run(df, group_fields=["g"], date_field="d", period="QUARTER").raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == 8 * 11
