import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "sales-documents.csv")


def run(df, **opts):
    return run_block(HERE, df, {"number_field": "n", **opts})


def test_gaps_duplicates_and_prefixes():
    df = pd.DataFrame({"n": ["INV-0001", "INV-0002", "INV-0005", "INV-0005", "INV-0009", "CN-01", "CN-02", "x", None]})
    res = run(df, max_missing_listed=2).raise_for_error()
    g = res.output(0)
    assert g["Missing Count"].tolist() == [2, 3] and g["Missing Numbers"].tolist() == ["INV-0003, INV-0004", "INV-0006, INV-0007, ..."]
    p = res.output(1)
    assert (p["Problem"] == "Duplicate number").sum() == 2
    s = res.output(2).set_index("Series")
    assert s.loc["INV-", "Missing"] == 5 and s.loc["CN-", "Missing"] == 0 and np.isclose(s.loc["INV-", "Completeness"], 4 / 9)
    assert "without a number skipped" in res.final_message


def test_date_order_and_series_field():
    df = pd.DataFrame({"n": [1, 2, 3, 1], "s": ["a", "a", "a", "b"], "d": ["2025-01-01", "2025-01-05", "2025-01-03", "2025-01-01"]})
    res = run(df, series_field="s", date_field="d").raise_for_error()
    p = res.output(1)
    assert p["Document"].tolist() == ["3"] and "dated 2025-01-03" in p["Detail"].iloc[0]
    assert set(res.output(2)["Series"]) == {"a", "b"}


def test_sample_and_large():
    res = run_block(HERE, SAMPLE, {"number_field": "Document No", "date_field": "Document Date"}).raise_for_error()
    s = res.output(2).set_index("Series")
    assert s.loc["INV-", "Missing"] == 5 and s.loc["CN-", "Missing"] == 1 and s.loc["INV-", "Duplicate Rows"] == 2
    assert (res.output(1)["Problem"] == "Dated before an earlier number").sum() >= 1
    assert run(pd.DataFrame({"n": [1]}), number_field="zz").status == "aborted"
    big = pd.DataFrame({"n": [f"T{k:07d}" for k in np.random.default_rng(0).choice(500_000, 300_000, replace=False)]})
    t0 = time.time()
    r = run(big).raise_for_error()
    assert time.time() - t0 < 120 and r.output(2)["Documents"].iloc[0] == 300_000
