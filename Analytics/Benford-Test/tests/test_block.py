import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "expense-claims.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"value_field": "v", **opts})


def benford_like(n, seed=0):
    return np.exp(np.random.default_rng(seed).uniform(np.log(10), np.log(1e6), n))  # log-uniform: exact Benford


def test_conforming_data_passes():
    res = run(pd.DataFrame({"v": benford_like(20000)})).raise_for_error()
    s = res.output(1).iloc[0]
    assert s["Conformity"] == "Close conformity" and s["P Value"] > 0.001
    d = res.output(0)
    assert d["Digit"].tolist() == list(range(1, 10))
    assert abs(d["Expected Share"].iloc[0] - np.log10(2)) < 1e-12
    assert len(res.output(2)) == 0


def test_manipulated_group_is_flagged_on_sample():
    res = run_block(HERE, SAMPLE, {"value_field": "Amount", "group_fields": ["Department"]}).raise_for_error()
    s = res.output(1).set_index("Department")
    assert s.loc["Field Engineering", "Conformity"] == "Nonconformity"
    assert s.loc["Field Engineering", "Over-represented Digits"].startswith("4")
    assert (s.drop("Field Engineering")["Conformity"] != "Nonconformity").all()
    flagged = res.output(2)
    assert len(flagged) > 0 and (flagged["Department"] == "Field Engineering").all() and (flagged["Tested Digits"] == 4).all()


def test_chi_square_matches_scipy():
    stats = pytest.importorskip("scipy.stats")
    v = np.concatenate([benford_like(3000, 1), np.full(200, 77.0)])
    s = run(pd.DataFrame({"v": v})).raise_for_error().output(1).iloc[0]
    counts = pd.Series([int(str(int(x))[0]) for x in v]).value_counts().reindex(range(1, 10), fill_value=0).to_numpy()
    exp = np.log10(1 + 1 / np.arange(1, 10)) * len(v)
    ref = stats.chisquare(counts, exp)
    assert abs(s["Chi-Square"] - ref.statistic) < 1e-6 and abs(s["P Value"] - ref.pvalue) < 1e-9


def test_first_two_and_second_digit_tests():
    v = pd.DataFrame({"v": benford_like(50000, 2)})
    two = run(v, test="FIRST_TWO").raise_for_error()
    assert two.output(0)["Digit"].tolist() == list(range(10, 100))
    sec = run(v, test="SECOND").raise_for_error().output(0)
    assert sec["Digit"].tolist() == list(range(10)) and abs(sec["Expected Share"].sum() - 1) < 1e-9
    assert abs(sec["Expected Share"].iloc[0] - 0.11968) < 1e-4


def test_digit_extraction_is_exact():
    v = pd.DataFrame({"v": [100.0, 199.99, 0.5, 12.0, 9.99, -45.0, 1e-3, 1000000.0]})
    d = run(v, min_value=0.0001, min_records=1).raise_for_error().output(0).set_index("Digit")["Count"]
    assert d[1] == 5 and d[4] == 1 and d[5] == 1 and d[9] == 1


def test_small_groups_and_min_value():
    v = pd.DataFrame({"v": [15.0, 25.0, 5.0, 3.0], "g": ["a", "a", "b", "b"]})
    s = run(v, group_fields=["g"]).raise_for_error().output(1).set_index("g")
    assert s.loc["a", "Values Tested"] == 2 and s.loc["b", "Values Tested"] == 0
    assert s.loc["a", "Conformity"].startswith("Too few") and s.loc["b", "Conformity"] == "No usable values"


def test_empty_and_wrong_types():
    res = run(pd.DataFrame({"v": pd.Series([], dtype="float64")})).raise_for_error()
    assert res.output(1)["Conformity"].iloc[0] == "No usable values"
    res = run(pd.DataFrame({"v": ["12", "abc", None, "34.5"]}), min_records=1).raise_for_error()
    assert res.output(1)["Values Tested"].iloc[0] == 2
    assert run(pd.DataFrame({"w": [1.0]})).status == "aborted"


def test_large_input_is_fast():
    df = pd.DataFrame({"v": benford_like(2_000_000, 5), "g": np.arange(2_000_000) % 200})
    t0 = time.time()
    res = run(df, group_fields=["g"]).raise_for_error()
    assert time.time() - t0 < 60 and len(res.output(1)) == 200
