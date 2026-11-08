import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "divisional-sales.csv")
DF = pd.DataFrame({"a": ["x", "x", "x", "y"], "b": ["p", "q", "q", "p"], "v": [1.0, 2.0, 3.0, 10.0]})


def run(df, **opts):
    return run_block(HERE, df, {"group_fields": ["a", "b"], "value_fields": ["v"], **opts})


def test_rows_order_and_values():
    r = run(DF).raise_for_error().output(0)
    assert r["Row Type"].tolist() == ["Grand total", "Subtotal", "Detail", "Subtotal", "Detail", "Detail"]
    assert r["v"].tolist() == [16.0, 10.0, 10.0, 6.0, 5.0, 1.0] and r["Order"].tolist() == list(range(1, 7))
    assert np.isclose(r["Share Of Parent"].iloc[4], 5 / 6) and np.isclose(r["Share Of Total"].iloc[3], 6 / 16)
    assert r["Label"].iloc[4] == "\u00b7 q" and r["Rows"].iloc[3] == 3


def test_options():
    r = run(DF, sort="NAME", subtotal_position="AFTER", total_label="All").raise_for_error().output(0)
    assert r["Row Type"].tolist() == ["Detail", "Detail", "Subtotal", "Detail", "Subtotal", "Grand total"]
    assert r["Label"].iloc[2] == "x All" and r["Label"].iloc[-1] == "All"
    m = run(DF, aggregation="MEAN", grand_total=False).raise_for_error().output(0)
    assert "Grand total" not in set(m["Row Type"]) and np.isclose(m[m["Label"] == "x"]["v"].iloc[0], 2.0)
    c = run(DF, aggregation="COUNT", value_fields=[]).raise_for_error().output(0)
    assert c["Rows"].iloc[0] == 4


def test_sample_and_consistency():
    r = run_block(HERE, SAMPLE, {"group_fields": ["Division", "Region", "Site"], "value_fields": ["Revenue (GBP k)"]}).raise_for_error().output(0)
    det = r[r["Row Type"] == "Detail"]["Revenue (GBP k)"].sum()
    assert np.isclose(det, r[r["Row Type"] == "Grand total"]["Revenue (GBP k)"].iloc[0])
    sub = r[(r["Row Type"] == "Subtotal") & (r["Level"] == 1)]
    assert np.isclose(sub["Share Of Total"].sum(), 1.0) and len(sub) == 3


def test_bad_inputs_and_large():
    assert run(DF, group_fields=[]).status == "aborted"
    assert run(DF, value_fields=["zz"]).status == "aborted"
    assert run(DF.assign(v="x")).status == "aborted"
    assert len(run(DF.iloc[0:0]).raise_for_error().output(0)) == 0
    rng = np.random.default_rng(0)
    big = pd.DataFrame({"a": rng.choice(list("abcde"), 400_000), "b": rng.choice([f"b{i}" for i in range(40)], 400_000), "v": rng.normal(size=400_000)})
    t0 = time.time()
    r = run(big).raise_for_error().output(0)
    assert time.time() - t0 < 120 and len(r) == 1 + 5 + 200
