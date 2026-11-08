import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "area-profiles.csv")


def run(df, **opts):
    return run_block(HERE, df, opts)


def two_factor(n=300, seed=0):
    rng = np.random.default_rng(seed)
    a, b = rng.normal(size=n), rng.normal(size=n)
    return pd.DataFrame({"a1": a + rng.normal(0, .1, n), "a2": 10 * a + rng.normal(0, 1, n), "a3": -a + rng.normal(0, .1, n),
                         "b1": b + rng.normal(0, .1, n), "b2": 100 * b + rng.normal(0, 10, n), "id": np.arange(n)})


def test_eigenvalues_match_correlation_matrix_and_kaiser():
    df = two_factor()
    res = run(df, fields=["a1", "a2", "a3", "b1", "b2"]).raise_for_error()
    c = res.output(0)
    ev = np.sort(np.linalg.eigvalsh(np.corrcoef(df[["a1", "a2", "a3", "b1", "b2"]].to_numpy().T)))[::-1]
    assert np.allclose(c["Eigenvalue"], ev) and np.isclose(c["Cumulative Share"].iloc[-1], 1.0)
    assert c["Kept"].tolist()[:3] == ["Yes", "Yes", "No"]
    l = res.output(1)
    pc1 = l[l["Component"] == "PC1"].set_index("Field")["Correlation With Component"]
    assert set(pc1.abs().nlargest(3).index) == {"a1", "a2", "a3"} and pc1["a3"] * pc1["a1"] < 0


def test_scores_reproducible_signs_and_missing():
    df = two_factor()
    df.loc[[3, 7], "b2"] = np.nan
    s = run(df, fields=["a1", "a2", "a3", "b1", "b2"]).raise_for_error().output(2)
    assert s["PC1"].isna().sum() == 2 and np.isclose(s["PC1"].mean(), 0, atol=0.2)
    assert np.isclose(s["PC1"].var(), run(df, fields=["a1", "a2", "a3", "b1", "b2"]).raise_for_error().output(0)["Eigenvalue"].iloc[0], rtol=0.05)
    l = run(df, fields=["a1", "a2", "a3", "b1", "b2"]).raise_for_error().output(1)
    for k, g in l.groupby("Component"):
        assert g.loc[g["Loading"].abs().idxmax(), "Loading"] > 0


def test_covariance_mode_fixed_components_and_target():
    df = two_factor()
    c = run(df, fields=["a1", "a2", "a3", "b1", "b2"], standardise=False).raise_for_error().output(0)
    assert c["Variance Share"].iloc[0] > 0.95  # b2 has by far the largest variance
    s = run(df, fields=["a1", "a2", "a3", "b1", "b2"], components=4).raise_for_error().output(2)
    assert {"PC1", "PC2", "PC3", "PC4"} <= set(s.columns) and "PC5" not in s.columns
    assert np.allclose(run(df, fields=["a1", "a2", "a3", "b1", "b2"], components=5).raise_for_error().output(2)["Unexplained Distance"], 0, atol=1e-9)


def test_sample_and_bad_inputs():
    res = run(SAMPLE).raise_for_error()
    assert (res.output(0)["Kept"] == "Yes").sum() == 3 and len(res.output(2)) == 400
    assert run(SAMPLE, fields=["Region", "Area Code"]).status == "aborted"
    assert run(SAMPLE, fields=["Over 65s %"]).status == "aborted"
    assert run(two_factor().assign(k=1.0), fields=["a1", "k"]).status == "aborted"
    assert run(two_factor().head(2), fields=["a1", "b1"]).status == "aborted"


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(300_000, 30)) @ rng.normal(size=(30, 30)), columns=[f"c{i}" for i in range(30)])
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(2)) == 300_000
