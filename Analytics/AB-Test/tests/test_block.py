import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "checkout-experiment.csv")
SUMMARY = os.path.join(HERE, "sample-data", "checkout-experiment-summary.csv")
BASE = {"variant_field": "Variant", "metric_field": "Converted", "control": "A"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**BASE, **opts})


def test_sample_b_wins_c_does_not():
    res = run(SAMPLE).raise_for_error()
    out = res.output(0).set_index("Variant")
    assert out.loc["B", "Significant"] == "Yes" and out.loc["C", "Significant"] == "No"
    assert abs(out.loc["B", "Relative Lift"] - 0.2) < 1e-9
    assert out.loc["B", "Difference CI Low"] > 0 > out.loc["C", "Difference CI Low"]
    assert "better" in out.loc["B", "Verdict"]
    v = res.output(1).set_index("Variant")
    assert v.loc["A", "Is Control"] == "Yes" and v.loc["A", "Sample Size"] == 8000


def test_two_proportion_z_matches_textbook():
    stats = pytest.importorskip("scipy.stats")
    df = pd.DataFrame({"Variant": ["A"] * 1000 + ["B"] * 1000,
                       "Converted": [1] * 100 + [0] * 900 + [1] * 130 + [0] * 870})
    out = run(df).raise_for_error().output(0).iloc[0]
    p_pool = 230 / 2000
    z = (0.13 - 0.10) / np.sqrt(p_pool * (1 - p_pool) * (2 / 1000))
    assert abs(out["Test Statistic"] - z) < 1e-9
    assert abs(out["P Value"] - 2 * stats.norm.sf(z)) < 1e-9


def test_welch_t_matches_scipy():
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(0)
    a, b = rng.normal(50.5, 10, 300), rng.normal(53.5, 14, 250)
    df = pd.DataFrame({"Variant": ["A"] * 300 + ["B"] * 250, "Value": np.concatenate([a, b])})
    out = run(df, metric_field="Value", metric_type="MEAN").raise_for_error().output(0).iloc[0]
    ref = stats.ttest_ind(b, a, equal_var=False)
    assert abs(out["Test Statistic"] - ref.statistic) < 1e-9
    assert abs(out["P Value"] - ref.pvalue) < 1e-8


def test_summary_layout_equals_row_layout():
    rows = run(SAMPLE).raise_for_error().output(0)
    summ = run(SUMMARY, layout="SUMMARY", trials_field="Visitors", successes_field="Conversions").raise_for_error().output(0)
    assert np.allclose(rows["P Value"], summ["P Value"]) and list(rows["Variant"]) == list(summ["Variant"])


def test_segments_and_bonferroni():
    plain = run(SAMPLE, segment_fields=["Device"]).raise_for_error().output(0)
    bonf = run(SAMPLE, segment_fields=["Device"], bonferroni=True).raise_for_error().output(0)
    assert len(plain) == 4 and set(plain["Device"]) == {"Desktop", "Mobile"}
    assert (bonf["Significant"] == "Yes").sum() <= (plain["Significant"] == "Yes").sum()


def test_outcome_encodings_and_default_control():
    df = pd.DataFrame({"Variant": ["x", "x", "y", "y"], "Converted": [True, False, "yes", "no"]})
    res = run_block(HERE, df, {"variant_field": "Variant", "metric_field": "Converted"}).raise_for_error()
    assert res.output(0)["Control"].iloc[0] == "x"


def test_unknown_control_and_bad_options():
    res = run(SAMPLE, control="Z").raise_for_error()
    assert len(res.output(0)) == 0 and "not found" in res.final_message
    assert run(SAMPLE, metric_field="nope").status == "aborted"
    assert run(SAMPLE, confidence=1.5).status == "aborted"
    assert run(SUMMARY, layout="SUMMARY", trials_field="Visitors", successes_field="Conversions", metric_type="MEAN").status == "aborted"


def test_empty_input_and_wrong_types():
    empty = pd.DataFrame({"Variant": pd.Series([], dtype=object), "Converted": pd.Series([], dtype=object)})
    res = run(empty).raise_for_error()
    assert len(res.output(0)) == 0 and "P Value" in res.output(0).columns
    df = pd.DataFrame({"Variant": ["A", "B", None], "Converted": ["maybe", "yes", "yes"]})
    out = run(df).raise_for_error().output(0)
    assert out["Verdict"].iloc[0].startswith("No significant") or out["Verdict"].iloc[0].startswith("Not enough")


def test_large_input_is_fast():
    n = 1_000_000
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"Variant": rng.choice(["A", "B", "C", "D"], n), "Converted": (rng.random(n) < 0.05).astype(int),
                       "Seg": rng.choice(["s1", "s2", "s3"], n)})
    t0 = time.time()
    out = run(df, segment_fields=["Seg"]).raise_for_error().output(0)
    assert time.time() - t0 < 60 and len(out) == 9
