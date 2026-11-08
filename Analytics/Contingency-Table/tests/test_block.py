import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "support-contacts.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"row_field": "r", "col_field": "c", **opts})


def agg():
    return pd.DataFrame({"r": ["a", "a", "b", "b"], "c": ["x", "y", "x", "y"], "n": [30, 10, 10, 30]})


def test_weighted_2x2_against_scipy():
    stats = pytest.importorskip("scipy.stats")
    res = run(agg(), weight_field="n").raise_for_error()
    t = res.output(1).iloc[0]
    ref = stats.chi2_contingency([[30, 10], [10, 30]], correction=False)
    assert abs(t["Chi-Square"] - ref.statistic) < 1e-9 and abs(t["P Value"] - ref.pvalue) < 1e-12
    assert abs(t["Cramer's V"] - np.sqrt(ref.statistic / 80)) < 1e-12
    yt = run(agg(), weight_field="n", yates=True).raise_for_error().output(1).iloc[0]
    ref_y = stats.chi2_contingency([[30, 10], [10, 30]], correction=True)
    assert abs(yt["Chi-Square"] - ref_y.statistic) < 1e-9
    cells = res.output(0).set_index(["r", "c"])
    assert cells.loc[("a", "x"), "Expected Count"] == 20 and cells.loc[("a", "x"), "Notable"] == "Over-represented"
    assert abs(cells.loc[("a", "x"), "Row Share"] - 0.75) < 1e-12


def test_rows_unweighted_sample():
    res = run_block(HERE, SAMPLE, {"row_field": "Channel", "col_field": "Outcome"}).raise_for_error()
    t = res.output(1).iloc[0]
    assert t["Rows"] == 5 and t["Columns"] == 3 and t["Sample Size"] == 1900 and t["P Value"] < 0.001
    assert "associated" in t["Verdict"]
    cells = res.output(0)
    assert cells["Count"].sum() == 1900 and cells["Count"].dtype == "int64"


def test_independent_data_not_significant():
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"r": rng.choice(list("abc"), 3000), "c": rng.choice(list("xy"), 3000)})
    t = run(df).raise_for_error().output(1).iloc[0]
    assert t["P Value"] > 0.01 and t["Verdict"].startswith("No significant")


def test_segments_blanks_and_small_expected():
    df = pd.DataFrame({"r": ["a", "b", None, "a", "b", "a"], "c": ["x", "y", "x", "y", "x", "x"], "s": ["s1"] * 3 + ["s2"] * 3})
    res = run(df, segment_fields=["s"]).raise_for_error()
    assert len(res.output(1)) == 2
    t = run(df, include_blank=True).raise_for_error().output(1).iloc[0]
    assert t["Rows"] == 3 and "Caution" in t["Verdict"]


def test_degenerate_and_bad_options():
    one = pd.DataFrame({"r": ["a", "a"], "c": ["x", "y"]})
    assert "at least two" in run(one).raise_for_error().output(1).iloc[0]["Verdict"]
    assert run(agg(), col_field="r").status == "aborted"
    assert run(agg(), weight_field="nope").status == "aborted"
    empty = pd.DataFrame({"r": pd.Series([], dtype=object), "c": pd.Series([], dtype=object)})
    assert len(run(empty).raise_for_error().output(0)) == 0


def test_large_input_is_fast():
    n = 2_000_000
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"r": rng.integers(0, 20, n), "c": rng.integers(0, 10, n)})
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 60 and len(res.output(0)) == 200
