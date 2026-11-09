import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
STOCK = os.path.join(HERE, "sample-data", "stock.csv")
MOVES = os.path.join(HERE, "sample-data", "movements.csv")
O = {"item_field": "i", "stock_field": "s", "move_item_field": "i", "move_date_field": "d", "move_qty_field": "q", "move_type_field": "t"}


def run(items, moves, **opts):
    return run_block(HERE, [items, moves] if moves is not None else items, {**O, **opts})


def test_run_out_before_receipt_and_projection():
    items = pd.DataFrame({"i": ["a"], "s": [10.0], "ss": [5.0]})
    moves = pd.DataFrame({"i": ["a"] * 6, "d": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05", "2025-01-05"],
                          "q": [4, 4, 4, 4, 20, 4], "t": ["Forecast", "Forecast", "Forecast", "Forecast", "PO 123", "Forecast"]})
    res = run(items, moves, safety_field="ss", horizon_days=6).raise_for_error()
    r = res.output(0).iloc[0]
    assert r["Run-Out Date"].strftime("%Y-%m-%d") == "2025-01-03" and r["Days Until Run-Out"] == 2
    assert r["First Day Below Safety Stock"].strftime("%Y-%m-%d") == "2025-01-02" and r["Next Receipt"].strftime("%Y-%m-%d") == "2025-01-05"
    assert r["Status"] == "Runs out before next receipt" and r["Lowest Projected Stock"] == -6 and r["Shortfall"] == 6
    p = res.output(1)
    assert p["Closing Stock"].tolist() == [6, 2, -2, -6, 10, 10] and p["Receipts"].iloc[4] == 20


def test_daily_demand_ok_and_below_safety():
    items = pd.DataFrame({"i": ["a", "b", "c"], "s": [100.0, 30.0, 10.0], "ss": [10, 25, 0], "dd": [1.0, 0.5, 1.0]})
    res = run_block(HERE, items, {"item_field": "i", "stock_field": "s", "safety_field": "ss", "daily_demand_field": "dd", "horizon_days": 20,
                                  "start_date": "2025-03-01"}).raise_for_error()
    r = res.output(0).set_index("i")
    assert r.loc["a", "Status"] == "OK" and r.loc["b", "Status"] == "Below safety stock" and r.loc["c", "Status"].startswith("Runs out")
    assert np.isclose(r.loc["a", "Days Of Cover (no receipts)"], 100) and r.index[0] == "c"  # urgent first


def test_receipt_words_unknown_items_and_late_receipts():
    items = pd.DataFrame({"i": ["a"], "s": [5.0]})
    moves = pd.DataFrame({"i": ["a", "a", "zz"], "d": ["2025-01-01", "2025-01-01", "2025-01-01"], "q": [10, 3, 5], "t": ["Forecast", "Goods in", "Forecast"]})
    res = run(items, moves, horizon_days=3).raise_for_error()
    r = res.output(0).iloc[0]
    assert r["Receipts In Horizon"] == 0 and "unknown items" in res.final_message  # "Goods in" is not one of the default receipt words
    res2 = run(items, moves, horizon_days=3, receipt_words="goods in").raise_for_error()
    assert res2.output(0).iloc[0]["Receipts In Horizon"] == 3 and res2.output(0).iloc[0]["Status"] == "Runs out (receipts too small or late)"


def test_sample_and_bad_inputs():
    res = run_block(HERE, [STOCK, MOVES], {"item_field": "SKU", "stock_field": "On Hand", "safety_field": "Safety Stock", "move_item_field": "SKU",
                                           "move_date_field": "Date", "move_qty_field": "Quantity", "move_type_field": "Type", "horizon_days": 60}).raise_for_error()
    assert len(res.output(0)) == 40 and len(res.output(1)) == 2400
    items = pd.DataFrame({"i": ["a"], "s": [5.0]})
    assert run_block(HERE, items, {"item_field": "i", "stock_field": "s"}).status == "aborted"  # no demand at all
    assert run(items, pd.DataFrame({"i": ["a"], "d": ["2025-01-01"], "q": [1], "t": ["x"]}), horizon_days=0).status == "aborted"
    assert run(items, pd.DataFrame({"i": ["a"]}), horizon_days=5).status == "aborted"


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    items = pd.DataFrame({"i": [f"s{k}" for k in range(2000)], "s": rng.uniform(0, 500, 2000)})
    d = pd.date_range("2025-01-01", periods=90).strftime("%Y-%m-%d")
    moves = pd.DataFrame({"i": np.repeat(items["i"], 90), "d": np.tile(d, 2000), "q": rng.poisson(5, 180_000), "t": "Forecast"})
    t0 = time.time()
    res = run(items, moves, horizon_days=90).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(1)) == 180_000
