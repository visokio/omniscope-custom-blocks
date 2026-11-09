import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "supplier-spend.csv")


def run(df, **opts):
    return run_block(HERE, df, {"entity_field": "e", "value_field": "v", **opts})


def test_known_values():
    df = pd.DataFrame({"e": ["a", "b", "c", "d", "a"], "v": [30.0, 30.0, 20.0, 10.0, 10.0]})  # a = 40 after summing
    s = run(df).raise_for_error().output(0).iloc[0]
    assert np.isclose(s["HHI"], 40 ** 2 + 30 ** 2 + 20 ** 2 + 10 ** 2) and s["Entities"] == 4
    assert np.isclose(s["Equivalent Equal Entities"], 10000 / 3000) and np.isclose(s["Top 1 Share"], 0.4) and np.isclose(s["Top 4 Share (CR4)"], 1.0)
    x = np.array([10, 20, 30, 40.0])
    gini = (2 * np.sum(np.arange(1, 5) * x)) / (4 * x.sum()) - 5 / 4
    assert np.isclose(s["Gini"], gini) and s["Entities For 50%"] == 2 and s["HHI Band"] == "Highly concentrated"


def test_equal_shares_and_bands():
    eq = pd.DataFrame({"e": list("abcdefghij"), "v": 1.0})
    s = run(eq).raise_for_error().output(0).iloc[0]
    assert np.isclose(s["HHI"], 1000) and np.isclose(s["Gini"], 0) and np.isclose(s["Normalised HHI"], 0) and s["HHI Band"] == "Unconcentrated"
    s = run(eq, hhi_moderate=500, hhi_high=2000).raise_for_error().output(0).iloc[0]
    assert s["HHI Band"] == "Moderately concentrated"
    assert run(eq, hhi_moderate=3000, hhi_high=2000).status == "aborted"


def test_lorenz_entities_groups_and_negatives():
    df = pd.DataFrame({"e": ["a", "b", "c", "a", "b", "z"], "v": [5.0, 3.0, 2.0, 1.0, 1.0, -4.0], "g": ["x", "x", "x", "y", "y", "y"]})
    res = run(df, group_fields=["g"]).raise_for_error()
    lor = res.output(1)
    assert len(lor) == 202 and np.isclose(lor.groupby("g")["Share Of Total"].max(), 1.0).all()
    assert (lor.groupby("g")["Share Of Total"].apply(lambda s: s.is_monotonic_increasing)).all()
    e = res.output(2)
    assert e[e["g"] == "x"]["Rank"].tolist() == [1, 2, 3] and "z" not in set(e["e"]) and "left out" in res.final_message


def test_sample_spend():
    s = run_block(HERE, SAMPLE, {"entity_field": "Supplier", "value_field": "Spend (GBP)", "group_fields": ["Year"]}).raise_for_error().output(0).set_index("Year")
    assert s.loc["2025", "HHI"] > s.loc["2023", "HHI"] and s.loc["2025", "Entities"] < s.loc["2023", "Entities"]


def test_bad_inputs_and_large():
    assert run(pd.DataFrame({"e": ["a"], "v": ["x"]})).status == "aborted"
    assert run(pd.DataFrame({"e": ["a"], "v": [1.0]}), entity_field="zz").status == "aborted"
    assert len(run(pd.DataFrame({"e": pd.Series([], dtype=object), "v": pd.Series([], dtype=float)})).raise_for_error().output(0)) == 0
    rng = np.random.default_rng(0)
    big = pd.DataFrame({"e": rng.integers(0, 50_000, 500_000).astype(str), "v": rng.pareto(1.2, 500_000), "g": rng.choice(list("abcd"), 500_000)})
    t0 = time.time()
    res = run(big, group_fields=["g"]).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == 4
