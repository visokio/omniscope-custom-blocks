import math
import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
BIDS = os.path.join(HERE, "sample-data", "supplier-bids.csv")
CRIT = os.path.join(HERE, "sample-data", "criteria.csv")
ALT = pd.DataFrame({"n": ["a", "b", "c"], "price": [100.0, 150.0, 200.0], "quality": [5.0, 9.0, 10.0]})


def run(inputs, **opts):
    return run_block(HERE, inputs, {"name_field": "n", **opts})


def test_min_max_weights_and_direction():
    res = run(ALT, criteria_fields=["price", "quality"], lower_better_fields=["price"], weights="price: 60, quality: 40").raise_for_error()
    o = res.output(0).set_index("n")
    assert math.isclose(o.loc["a", "price Score"], 100) and math.isclose(o.loc["c", "price Score"], 0)
    assert math.isclose(o.loc["b", "quality Score"], 80)
    assert math.isclose(o.loc["a", "Total Score"], 60) and math.isclose(o.loc["b", "Total Score"], 0.6 * 50 + 0.4 * 80)
    assert o.loc["b", "Rank"] == 1 and o.loc["a", "Rank"] == 2 and o.loc["b", "Leader"] == "Yes"
    assert math.isclose(o.loc["b", "price Points"] + o.loc["b", "quality Points"], o.loc["b", "Total Score"])
    c = res.output(1).set_index("Criterion")
    assert c.loc["price", "Leader"] == "b" and c.loc["price", "New Leader"] == "a"  # b leads 62 to 60
    long = res.output(2)
    assert len(long) == 6 and set(long["Criterion"]) == {"price", "quality"}


def test_weights_in_order_equal_and_errors():
    o = run(ALT, criteria_fields=["price", "quality"], weights="1, 3").raise_for_error().output(1)
    assert np.allclose(o["Weight Share"], [0.25, 0.75])
    o = run(ALT, criteria_fields=["price", "quality"]).raise_for_error().output(1)
    assert np.allclose(o["Weight Share"], [0.5, 0.5])
    assert run(ALT, criteria_fields=["price", "quality"], weights="1").status == "aborted"
    assert run(ALT, criteria_fields=["price", "quality"], weights="size: 3").status == "aborted"
    assert run(ALT, criteria_fields=["price", "quality"], weights="price: 0, quality: 0").status == "aborted"
    assert run(ALT.assign(t=["x", "y", "z"]), criteria_fields=["t"]).status == "aborted"


def test_sensitivity_finds_the_flip_point():
    df = pd.DataFrame({"n": ["a", "b"], "x": [100.0, 0.0], "y": [0.0, 100.0]})
    c = run(df, criteria_fields=["x", "y"], weights="x: 60, y: 40").raise_for_error().output(1).set_index("Criterion")
    assert c.loc["x", "Leader"] == "a" and c.loc["x", "New Leader"] == "b"
    assert abs(c.loc["x", "Weight Share That Changes Leader"] - 0.5) <= 0.006
    assert "falls" in c.loc["x", "Sensitivity"]


def test_criteria_table_thresholds_and_sample():
    res = run_block(HERE, [BIDS, CRIT], {"name_field": "Supplier", "crit_name_field": "Criterion", "crit_weight_field": "Weight",
                                         "crit_direction_field": "Better When", "crit_min_field": "Minimum", "crit_max_field": "Maximum"}).raise_for_error()
    o = res.output(0).set_index("Supplier")
    assert o.loc["Supplier F", "Passes Thresholds"] == "No" and "Financial Risk" in o.loc["Supplier F", "Failed On"]
    assert pd.isna(o.loc["Supplier F", "Rank"]) and o.loc["Supplier H", "Criteria Missing"] == 1
    assert o["Rank"].dropna().tolist() == list(range(1, 10))
    assert (o["Total Score"].between(0, 100)).all()


def test_missing_modes_and_groups():
    df = pd.DataFrame({"n": list("abcd"), "g": ["x", "x", "y", "y"], "p": [1.0, 2.0, 3.0, np.nan], "q": [1.0, 0.0, 1.0, 1.0]})
    # group y: c has p=3, q=1; d has p missing, q=1. Single p value -> 100; q equal -> 100 for both
    for mode, expect in (("WORST", 50.0), ("AVERAGE", 75.0), ("REWEIGHT", 100.0)):
        o = run(df, criteria_fields=["p", "q"], group_fields=["g"], missing=mode).raise_for_error().output(0).set_index("n")
        assert math.isclose(o.loc["d", "Total Score"], expect) and pd.isna(o.loc["d", "p Score"])
        assert o.loc["c", "Rank"] == 1 and o.loc["a", "Rank"] == 1 and o.loc["b", "Rank"] == 1  # ranked within groups; a and b tie at 50


def test_methods_and_empty():
    for m in ("PERCENT_OF_BEST", "RANK", "Z_SCORE"):
        o = run(ALT, criteria_fields=["price", "quality"], lower_better_fields=["price"], method=m).raise_for_error().output(0)
        assert o["Total Score"].between(0, 100).all() and o["Rank"].notna().all()
    o = run(ALT, criteria_fields=["price"], lower_better_fields=["price"], method="PERCENT_OF_BEST").raise_for_error().output(0).set_index("n")
    assert math.isclose(o.loc["b", "price Score"], 100 * 100 / 150)
    res = run(ALT.iloc[0:0], criteria_fields=["price", "quality"]).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 2
    assert run(ALT, name_field="nope", criteria_fields=["price"]).status == "aborted"


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 20_000
    df = pd.DataFrame({"n": [f"s{i}" for i in range(n)], "g": rng.choice(list("abcdefghij"), n), **{f"c{j}": rng.normal(size=n) for j in range(8)}})
    t0 = time.time()
    res = run(df, criteria_fields=[f"c{j}" for j in range(8)], group_fields=["g"]).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == n and len(res.output(1)) == 80
