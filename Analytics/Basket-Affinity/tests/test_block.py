import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "grocery-baskets.csv")
F = {"basket_field": "b", "item_field": "i", "min_item_baskets": 1, "min_pair_baskets": 1}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**F, **opts})


def lines(baskets):
    return pd.DataFrame([{"b": k, "i": it} for k, its in baskets.items() for it in its])


def test_metrics_by_hand():
    df = lines({1: "AB", 2: "AB", 3: "A", 4: "C", 5: "BC"})
    pairs = run(df).raise_for_error().output(0).set_index(["Item A", "Item B"])
    ab = pairs.loc[("A", "B")]
    assert ab["Baskets With Both"] == 2 and abs(ab["Support"] - 0.4) < 1e-12
    assert abs(ab["Confidence A to B"] - 2 / 3) < 1e-12 and abs(ab["Confidence B to A"] - 2 / 3) < 1e-12
    assert abs(ab["Lift"] - 0.4 / (0.6 * 0.6)) < 1e-12 and abs(ab["Jaccard"] - 0.5) < 1e-12
    assert ("A", "C") not in pairs.index  # never together


def test_duplicate_lines_count_once_and_filters():
    df = lines({1: "AAB", 2: "AB", 3: "C"})
    pairs = run(df).raise_for_error().output(0)
    assert pairs.loc[0, "Baskets With Both"] == 2
    assert len(run(df, min_pair_baskets=3).raise_for_error().output(0)) == 0
    assert len(run(df, max_items=2).raise_for_error().output(1)) == 2


def test_sample_known_links():
    res = run_block(HERE, SAMPLE, {"basket_field": "Basket ID", "item_field": "Item"}).raise_for_error()
    pairs, items = res.output(0), res.output(1).set_index("Item")
    top = pairs.iloc[0]
    assert {top["Item A"], top["Item B"]} == {"Baby wipes", "Nappies"} and top["Lift"] > 5
    assert items.loc["Pasta", "Top Partners (by lift)"].startswith(("Pasta sauce", "Parmesan"))
    neg = pairs[(pairs["Item A"].isin(["Cat food", "Ice cream"])) & (pairs["Item B"].isin(["Cat food", "Ice cream"]))]
    assert len(neg) == 0 or neg["Lift"].iloc[0] < 1


def test_empty_wrong_and_single_item():
    res = run(pd.DataFrame({"b": pd.Series([], dtype=object), "i": pd.Series([], dtype=object)})).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0
    assert run(lines({1: "AB"}), item_field="b").status == "aborted"
    out = run(pd.DataFrame({"b": [1, 2], "i": [10, 10]})).raise_for_error()
    assert len(out.output(0)) == 0 and out.output(1)["Item"].tolist() == ["10"]


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 1_000_000
    df = pd.DataFrame({"b": rng.integers(0, 150_000, n), "i": rng.integers(0, 400, n)})
    t0 = time.time()
    res = run(df, max_items=200, min_pair_baskets=5).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(1)) == 200
