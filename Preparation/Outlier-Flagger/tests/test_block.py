import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "expense-claims.csv")
V = pd.DataFrame({"v": [10, 11, 12, 13, 14, 15, 16, 17, 18, 100.0, -50.0, 12.5], "w": [1.0] * 11 + [9.0], "g": ["a"] * 12})


def run(df, **opts):
    return run_block(HERE, df, opts)


def test_iqr_bounds_and_flags():
    res = run(V, fields=["v"], min_group_size=5).raise_for_error()
    b = res.output(2).iloc[0]
    q1, q3 = np.percentile(V["v"], [25, 75])
    assert np.isclose(b["Lower Bound"], q1 - 1.5 * (q3 - q1)) and np.isclose(b["Upper Bound"], q3 + 1.5 * (q3 - q1))
    r = res.output(0)
    assert r["v Outlier"].tolist()[9:11] == ["High", "Low"] and r["Outlier Count"].sum() == 2
    o = res.output(1)
    assert o["Row Number"].tolist() == [10, 11] and set(o["Direction"]) == {"High", "Low"}


def test_zscore_mad_k_and_capping():
    z = run(V, fields=["v"], method="ZSCORE", min_group_size=5).raise_for_error().output(2).iloc[0]
    assert np.isclose(z["Upper Bound"], V["v"].mean() + 3 * V["v"].std())
    m = run(V, fields=["v"], method="MAD", min_group_size=5).raise_for_error()
    med = V["v"].median()
    mad = np.median(np.abs(V["v"] - med))
    assert np.isclose(m.output(2).iloc[0]["Upper Bound"], med + 3.5 * mad / 0.6745)
    loose = run(V, fields=["v"], k=20, min_group_size=5).raise_for_error().output(1)
    assert len(loose) == 0
    c = run(V, fields=["v"], add_capped=True, min_group_size=5).raise_for_error().output(0)
    b = run(V, fields=["v"], min_group_size=5).raise_for_error().output(2).iloc[0]
    assert np.isclose(c["v Capped"].max(), b["Upper Bound"]) and np.isclose(c["v Capped"].min(), b["Lower Bound"])


def test_groups_min_size_and_all_numeric_default():
    df = pd.concat([V.assign(g="a"), V.head(4).assign(g="b")])
    res = run(df, group_fields=["g"], min_group_size=5).raise_for_error()
    b = res.output(2)
    assert set(b[b["g"] == "b"]["Tested"]) == {"No (too few values)"} and set(b["Field"]) == {"v", "w"}
    assert res.output(0)[res.output(0)["g"] == "b"]["v Outlier"].isna().all()


def test_sample_claims():
    res = run_block(HERE, SAMPLE, {"fields": ["Amount (GBP)", "Mileage", "Days To Submit"], "group_fields": ["Category"], "key_fields": ["Claim ID"]}).raise_for_error()
    o = res.output(1)
    assert {1450.0, 1800.0, 2100.0} <= set(o[o["Field"] == "Mileage"]["Value"]) and (o[o["Field"] == "Days To Submit"]["Value"] >= 75).sum() >= 5
    assert "Claim ID" in o.columns


def test_bad_inputs_and_large():
    assert run(V, fields=["zz"]).status == "aborted"
    assert run(V.assign(t="x"), fields=["t"]).status == "aborted"
    assert run(pd.DataFrame({"t": ["a"]})).status == "aborted"
    assert run(V, k=-1).status == "aborted"
    assert len(run(V.iloc[0:0], fields=["v"]).raise_for_error().output(1)) == 0
    rng = np.random.default_rng(0)
    big = pd.DataFrame({f"c{i}": rng.normal(size=300_000) for i in range(8)})
    big["g"] = rng.choice(list("abcdefghij"), 300_000)
    t0 = time.time()
    res = run(big, group_fields=["g"]).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(2)) == 80
