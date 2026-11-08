import os

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "purchases.csv")
DF = pd.DataFrame({"i": ["a", "b", "a", "b", "c"], "t": ["0", "0", "1", "1", "1"], "p": [1.0, 2.0, 2.0, 2.0, 5.0], "q": [10.0, 5.0, 5.0, 10.0, 1.0]})
O = {"item_field": "i", "period_field": "t", "price_field": "p", "quantity_field": "q"}


def test_index_formulas():
    o = run_block(HERE, DF, O).raise_for_error().output(0).set_index("Period")
    lasp = (2 * 10 + 2 * 5) / (1 * 10 + 2 * 5) * 100
    paas = (2 * 5 + 2 * 10) / (1 * 5 + 2 * 10) * 100
    assert np.isclose(o.loc["1", "Laspeyres"], lasp) and np.isclose(o.loc["1", "Paasche"], paas) and np.isclose(o.loc["1", "Fisher"], np.sqrt(lasp * paas))
    assert o.loc["0", "Fisher"] == 100 and o.loc["1", "Items Missing"] == 1
    assert np.isclose(o.loc["1", "Value Index"], (2 * 5 + 2 * 10) / 20 * 100)


def test_groups_base_sample_and_bad_inputs():
    g = run_block(HERE, pd.concat([DF.assign(g="x"), DF.assign(g="y")]), {**O, "group_field": "g", "base_period": "1"}).raise_for_error().output(0)
    assert set(g["g"]) == {"x", "y"} and (g[g["Period"] == "1"]["Fisher"] == 100).all()
    s = run_block(HERE, SAMPLE, {"item_field": "Item", "period_field": "Year", "price_field": "Unit Price (GBP)", "quantity_field": "Quantity"}).raise_for_error().output(0)
    assert len(s) == 5 and s["Fisher"].iloc[-1] > 110
    assert run_block(HERE, DF, {**O, "base_period": "9"}).status == "aborted"
    assert run_block(HERE, DF, {**O, "price_field": "zz"}).status == "aborted"
