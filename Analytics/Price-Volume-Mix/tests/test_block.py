import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "product-sales-2024-2025.csv")
F = {"period_field": "per", "item_field": "item", "volume_field": "q", "revenue_field": "r"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**F, **opts})


def rows(spec):
    return pd.DataFrame([{"per": p, "item": i, "q": q, "r": q * pr} for p, i, q, pr in spec])


def bridge(res):
    return res.output(0).set_index("Step")["Value"]


def test_pure_volume_mix_price():
    # same mix, volume doubles, no price change -> all volume
    b = bridge(run(rows([("y1", "a", 10, 2.5), ("y1", "b", 10, 5.0), ("y2", "a", 20, 2.5), ("y2", "b", 20, 5.0)])).raise_for_error())
    assert np.isclose(b["Volume"], 75) and np.isclose(b["Mix"], 0) and np.isclose(b["Price"], 0)
    # same total volume, shift to the dearer item -> all mix
    b = bridge(run(rows([("y1", "a", 10, 2.5), ("y1", "b", 10, 5.0), ("y2", "a", 5, 2.5), ("y2", "b", 15, 5.0)])).raise_for_error())
    assert np.isclose(b["Volume"], 0) and np.isclose(b["Mix"], 12.5) and np.isclose(b["Price"], 0)
    # price only
    b = bridge(run(rows([("y1", "a", 10, 2.5), ("y2", "a", 10, 3.0)])).raise_for_error())
    assert np.isclose(b["Price"], 5) and np.isclose(b["Volume"], 0)


def test_new_lost_and_exact_reconciliation():
    res = run(rows([("y1", "a", 10, 2.5), ("y1", "old", 4, 10.0), ("y2", "a", 12, 2.75), ("y2", "new", 3, 8.0)])).raise_for_error()
    b = bridge(res)
    assert np.isclose(b["New products"], 24) and np.isclose(b["Lost products"], -40)
    effects = b[["Volume", "Mix", "Price", "New products", "Lost products"]].sum()
    assert np.isclose(b["Base revenue"] + effects, b["Current revenue"])
    st = res.output(1).set_index("item" if "item" in res.output(1).columns else "Item")["Status"]
    assert st["new"] == "New" and st["old"] == "Lost"


def test_waterfall_columns_and_explicit_periods():
    df = rows([("2023", "a", 5, 1.5), ("2024", "a", 10, 2.5), ("2025", "a", 12, 2.5)])
    res = run(df, base_period="2023", current_period="2024").raise_for_error()
    b = res.output(0)
    assert b["Value"].iloc[0] == 7.5 and b["Value"].iloc[-1] == 25.0
    assert np.isclose(b["Bar End"].iloc[-2], b["Value"].iloc[-1])
    assert run(df, base_period="1999").status == "aborted"
    d = run(df).raise_for_error().output(0)
    assert d["Value"].iloc[0] == 7.5 and d["Value"].iloc[-1] == 30.0  # first and last by default


def test_sample_by_region():
    res = run_block(HERE, SAMPLE, {"period_field": "Year", "item_field": "Product", "volume_field": "Units", "revenue_field": "Revenue", "group_fields": ["Region"]}).raise_for_error()
    b = res.output(0)
    for reg, g in b.groupby("Region"):
        g = g.set_index("Step")["Value"]
        assert np.isclose(g["Base revenue"] + g[["Volume", "Mix", "Price", "New products", "Lost products"]].sum(), g["Current revenue"])
        assert g["Price"] > 0 and g["New products"] > 0 and g["Lost products"] < 0


def test_bad_and_degenerate():
    assert run(rows([("y1", "a", 1, 1.5)])).status == "aborted"  # one period only
    assert run(rows([("y1", "a", 1, 1.5), ("y2", "a", 1, 1.5)]), revenue_field="nope").status == "aborted"
    zero = run(pd.DataFrame({"per": ["y1", "y2"], "item": ["fee", "fee"], "q": [0.0, 0.0], "r": [10.5, 12.5]})).raise_for_error()
    b = bridge(zero)
    assert np.isclose(b["Current revenue"] - b["Base revenue"], b["New products"])


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 1_000_000
    df = pd.DataFrame({"per": rng.choice(["2024", "2025"], n), "item": rng.integers(0, 5000, n), "q": rng.integers(1, 20, n).astype(float), "g": rng.integers(0, 20, n)})
    df["r"] = df["q"] * (5 + df["item"] % 7) * np.where(df["per"] == "2025", 1.05, 1.0)
    t0 = time.time()
    res = run(df, group_fields=["g"]).raise_for_error()
    assert time.time() - t0 < 90 and len(res.output(0)) == 20 * 7
