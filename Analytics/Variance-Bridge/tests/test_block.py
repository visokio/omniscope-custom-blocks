import os

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "cost-centre-budget.csv")
DF = pd.DataFrame({"c": ["a", "b", "c", "a"], "b": [10.0, 20, 5, 0], "x": [12.0, 15, 6, 1]})


def run(df, **opts):
    return run_block(HERE, df, {"category_field": "c", "base_field": "b", "current_field": "x", **opts})


def test_bridge_steps_and_bars():
    r = run(DF).raise_for_error()
    b = r.output(0)
    assert b["Label"].tolist() == ["Budget", "b", "a", "c", "Actual"] and b["Value"].tolist() == [35.0, -5.0, 3.0, 1.0, 34.0]
    assert b["Bar Start"].tolist()[1:4] == [35.0, 30.0, 33.0] and b["Bar End"].iloc[3] == 34.0
    assert b["Direction"].tolist()[1:4] == ["Adverse", "Favourable", "Favourable"]
    lo = run(DF, better_when="LOWER").raise_for_error().output(0)
    assert lo["Direction"].iloc[1] == "Favourable"
    c = r.output(1).set_index("Category")
    assert np.isclose(c.loc["a", "Variance %"], 0.3)


def test_other_order_groups_labels():
    o = run(DF, top_n=1).raise_for_error().output(0)
    assert o["Label"].tolist() == ["Budget", "b", "Other (2)", "Actual"] and o["Value"].iloc[2] == 4.0
    n = run(DF, order="NAME", base_label="LY", current_label="TY").raise_for_error().output(0)
    assert n["Label"].tolist() == ["LY", "a", "b", "c", "TY"]
    g = run(DF.assign(r=["n", "n", "s", "s"]), group_field="r").raise_for_error().output(0)
    assert set(g["r"]) == {"n", "s"} and (g["Kind"] == "Total").sum() == 4


def test_sample_and_bad_inputs():
    r = run_block(HERE, SAMPLE, {"category_field": "Cost Line", "base_field": "Budget (GBP k)", "current_field": "Actual (GBP k)", "better_when": "LOWER"}).raise_for_error()
    b = r.output(0)
    assert b["Label"].iloc[1] == "Agency staff" and b["Direction"].iloc[1] == "Adverse" and np.isclose(b["Bar End"].iloc[-1], b["Value"].iloc[-1])
    assert np.isclose(b[b["Kind"] == "Variance"]["Share Of Total Variance"].sum(), 1.0)
    assert run(DF, base_field="zz").status == "aborted"
    assert len(run(DF.iloc[0:0]).raise_for_error().output(0)) == 0
