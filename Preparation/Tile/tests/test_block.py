import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "customer-revenue.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"value_field": "v", **opts})


def test_equal_records_quartiles():
    df = pd.DataFrame({"v": np.arange(1.5, 9.5)})  # 8 values
    out = run(df, tiles=4).raise_for_error().output(0)
    assert out["Tile Number"].tolist() == [1, 1, 2, 2, 3, 3, 4, 4]
    assert out["Tile Range"].iloc[0] == "1.5 to 2.5"
    hi = run(df, tiles=4, highest_first=True).raise_for_error().output(0)
    assert hi["Tile Number"].tolist() == [4, 4, 3, 3, 2, 2, 1, 1]


def test_equal_sum_bands_hold_equal_shares():
    res = run_block(HERE, SAMPLE, {"value_field": "Annual Revenue", "method": "EQUAL_SUM", "highest_first": True}).raise_for_error()
    summ = res.output(1)
    assert np.allclose(summ["Share Of Total"], 0.25, atol=0.03)
    assert summ.set_index("Tile Number").loc[1, "Records"] < summ.set_index("Tile Number").loc[4, "Records"]


def test_equal_width_and_constant_values():
    df = pd.DataFrame({"v": [0.5, 2.5, 5.0, 7.5, 10.5]})
    out = run(df, method="EQUAL_WIDTH", tiles=2).raise_for_error().output(0)
    assert out["Tile Number"].tolist() == [1, 1, 1, 2, 2]
    same = run(pd.DataFrame({"v": [3.0, 3.0]}), method="EQUAL_WIDTH").raise_for_error().output(0)
    assert same["Tile Number"].tolist() == [1, 1]


def test_smart_tile_labels():
    df = pd.DataFrame({"v": [10.5] * 20 + [1000.5]})
    out = run(df, method="SMART").raise_for_error().output(0)
    assert out["Tile Label"].iloc[-1] == "Extremely high"
    assert set(out["Tile Label"].iloc[:-1]) == {"Below average"}


def test_manual_cut_points():
    df = pd.DataFrame({"v": [50.5, 100.0, 499.5, 5000.5]})
    out = run(df, method="MANUAL", cut_points="100, 500").raise_for_error().output(0)
    assert out["Tile Number"].tolist() == [1, 2, 2, 3]
    assert run(df, method="MANUAL", cut_points="abc").status == "aborted"
    assert run(df, method="MANUAL").status == "aborted"


def test_within_groups():
    df = pd.DataFrame({"g": ["a"] * 4 + ["b"] * 4, "v": [1.5, 2.5, 3.5, 4.5, 100.5, 200.5, 300.5, 400.5]})
    res = run(df, tiles=2, group_fields=["g"]).raise_for_error()
    assert res.output(0)["Tile Number"].tolist() == [1, 1, 2, 2, 1, 1, 2, 2]
    s = res.output(1)
    assert len(s) == 4 and set(s.columns) >= {"g", "Tile Number", "Records", "Share Of Total"}


def test_nulls_and_text_numbers():
    df = pd.DataFrame({"v": ["1.5", None, "x", "4.5"]})
    out = run(df, tiles=2).raise_for_error().output(0)
    assert out["Tile Number"].isna().tolist() == [False, True, True, False]


def test_empty_input_and_bad_field():
    res = run(pd.DataFrame({"v": pd.Series([], dtype="float64")})).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0 and "Records" in res.output(1).columns
    assert run(pd.DataFrame({"w": [1.5]})).status == "aborted"
    assert run(pd.DataFrame({"v": ["a", "b"]})).status == "aborted"


def test_large_input_is_fast():
    n = 500_000
    df = pd.DataFrame({"v": np.random.default_rng(3).lognormal(size=n), "g": np.arange(n) % 50})
    t0 = time.time()
    out = run(df, tiles=10, group_fields=["g"]).raise_for_error().output(0)
    out2 = run(df, method="EQUAL_SUM", tiles=10).raise_for_error().output(0)
    assert time.time() - t0 < 60 and out["Tile Number"].between(1, 10).all() and len(out2) == n
