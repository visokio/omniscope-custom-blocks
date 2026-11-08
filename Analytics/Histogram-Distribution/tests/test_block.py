import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "order-values.csv")


def run(df, **opts):
    return run_block(HERE, df, {"value_field": "v", **opts})


def test_bins_counts_and_stats():
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"v": rng.normal(50, 10, 1000)})
    res = run(df).raise_for_error()
    h, s = res.output(0), res.output(1).iloc[0]
    assert h["Count"].sum() == 1000 and np.isclose(h["Cumulative Share"].iloc[-1], 1.0)
    iqr = np.subtract(*np.percentile(df["v"], [75, 25]))
    assert np.isclose(h["To"].iloc[0] - h["From"].iloc[0], 2 * iqr / 1000 ** (1 / 3))
    assert np.isclose(s["Skewness"], stats.skew(df["v"])) and np.isclose(s["Excess Kurtosis"], stats.kurtosis(df["v"]))
    assert np.isclose(s["Median"], df["v"].median())


def test_width_bins_sturges_groups_and_clip():
    df = pd.DataFrame({"v": list(range(100)) + [10_000], "g": ["a"] * 50 + ["b"] * 51})
    assert len(run(df, bins=5).raise_for_error().output(0)) >= 5
    w = run(df, bin_width=25).raise_for_error().output(0)
    assert np.isclose((w["To"] - w["From"]).iloc[0], 25)
    st = run(df, bin_rule="STURGES").raise_for_error().output(0)
    assert len(st) <= 9
    gres = run(df, group_field="g", clip_percentile=1).raise_for_error()
    h = gres.output(0)
    assert set(h["g"]) == {"a", "b", "All"} and h.groupby("g")["From"].min().nunique() == 1  # same bins for every group
    s = gres.output(1).set_index("g")
    assert s.loc["b", "Above Range"] >= 1 and s.loc["All", "Count"] == 101


def test_sample_and_bad_inputs():
    res = run_block(HERE, SAMPLE, {"value_field": "Order Value (GBP)", "group_field": "Channel"}).raise_for_error()
    s = res.output(1).set_index("Channel")
    assert s.loc["All", "Missing"] == 20 and s.loc["Phone", "Median"] > s.loc["Store", "Median"]
    assert run(pd.DataFrame({"v": ["a"]})).status == "aborted"
    assert run(pd.DataFrame({"v": [1.0]}), value_field="zz").status == "aborted"
    assert run(pd.DataFrame({"v": [5.0, 5.0]})).raise_for_error().output(0)["Count"].sum() == 2
    big = pd.DataFrame({"v": np.random.default_rng(1).lognormal(3, 1, 500_000), "g": np.random.default_rng(2).choice(list("abcdef"), 500_000)})
    t0 = time.time()
    run(big, group_field="g").raise_for_error()
    assert time.time() - t0 < 120
