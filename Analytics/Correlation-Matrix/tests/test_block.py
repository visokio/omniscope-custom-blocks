import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "store-performance.csv")


def run(df, **opts):
    return run_block(HERE, df, opts)


def data(n=200, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=n)
    return pd.DataFrame({"x": x, "y": 2 * x + rng.normal(0, 0.5, n), "z": rng.normal(size=n), "e": np.exp(3 * x), "g": rng.choice(["a", "b"], n)})


def test_values_match_scipy():
    stats = pytest.importorskip("scipy.stats")
    df = data()
    p = run(df).raise_for_error().output(0).set_index(["Field A", "Field B"])
    for a, b in (("x", "y"), ("x", "z"), ("y", "e")):
        pr, pp = stats.pearsonr(df[a], df[b])
        sr, sp = stats.spearmanr(df[a], df[b])
        row = p.loc[(a, b)]
        assert np.isclose(row["Pearson"], pr) and np.isclose(row["Pearson P Value"], pp, rtol=1e-6, atol=1e-300)
        assert np.isclose(row["Spearman"], sr) and np.isclose(row["Spearman P Value"], sp, rtol=1e-6, atol=1e-300)
    assert p.loc[("x", "e"), "Spearman"] > 0.999 > p.loc[("x", "e"), "Pearson"]  # monotonic but not linear


def test_labels_ranking_matrix_and_target():
    df = data()
    res = run(df).raise_for_error()
    p = res.output(0)
    assert p["Rank"].tolist() == list(range(1, 7)) and p.iloc[0]["Strength"] == "Very strong"
    assert p[(p["Field A"] == "x") & (p["Field B"] == "z")]["Significant"].iloc[0] == "No"
    m = res.output(1)
    assert len(m) == 16 and m[(m["Row Field"] == "x") & (m["Column Field"] == "x")]["Correlation"].iloc[0] == 1.0
    w = res.output(2)
    assert list(w.columns) == ["Field", "x", "y", "z", "e"] and np.allclose(w.set_index("Field").values, w.set_index("Field").values.T, equal_nan=True)
    t = run(df, target_field="y", method="SPEARMAN").raise_for_error().output(0)
    assert set(t["Field A"]) == {"y"} and len(t) == 3 and t.iloc[0]["Field B"] in ("x", "e")


def test_groups_missing_and_min_rows():
    df = data()
    df.loc[:150, "z"] = np.nan
    res = run(df, group_field="g", min_pairs=30).raise_for_error()
    p = res.output(0)
    assert set(p["Group"]) == {"All", "a", "b"} and p.iloc[0]["Group"] == "All"
    xz = p[(p["Field A"] == "x") & (p["Field B"] == "z")]
    assert xz[xz["Group"] == "All"]["Rows"].iloc[0] == 49 and xz[xz["Group"] != "All"]["Pearson"].isna().all()


def test_sample_and_bad_inputs():
    res = run(SAMPLE).raise_for_error()
    top = res.output(0).iloc[0]
    assert {top["Field A"], top["Field B"]} == {"Weekly Footfall", "Annual Sales (GBP k)"}
    assert run(SAMPLE, fields=["Region", "Store"]).status == "aborted"
    assert run(SAMPLE, fields=["Weekly Footfall"]).status == "aborted"
    assert run(SAMPLE, target_field="zz").status == "aborted"
    res = run(data().iloc[0:0]).raise_for_error()
    assert res.output(0)["Pearson"].isna().all()


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(200_000, 25)), columns=[f"c{i}" for i in range(25)])
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == 300


def test_sample_data_is_plausible():
    df = pd.read_csv(SAMPLE)
    for col in ("Floor Area (sq m)", "Weekly Footfall", "Staff Hours", "Annual Sales (GBP k)"):
        assert (df[col] > 0).all(), col  # counts, areas and sales cannot be negative
    assert df["Staff Hours"].min() >= 30
