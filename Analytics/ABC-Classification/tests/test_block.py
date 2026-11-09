import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "sku-monthly-sales.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"item_field": "i", "value_field": "v", **opts})


def test_abc_boundaries_and_aggregation():
    df = pd.DataFrame({"i": ["a", "b", "c", "d", "e", "a"], "v": [40.5, 30.5, 15.5, 8.5, 5.0, 0.0]})
    res = run(df).raise_for_error()
    out = res.output(0).set_index("i")
    # shares: a .405 b .305 (cum .71) c .155 (starts at .71 -> A) d .085 (starts .865 -> B) e .05 (starts .95 -> C)
    assert out["ABC Class"].to_dict() == {"a": "A", "b": "A", "c": "A", "d": "B", "e": "C"}
    assert out.loc["a", "Rank"] == 1 and abs(out["Cumulative Share"].max() - 1) < 1e-12
    s = res.output(1).set_index("ABC Class")
    assert s.loc["A", "Items"] == 3 and abs(s["Share Of Value"].sum() - 1) < 1e-9


def test_thresholds_and_groups():
    df = pd.DataFrame({"g": ["x"] * 3 + ["y"] * 3, "i": list("abcdef"), "v": [80.5, 12.5, 7.0, 10.5, 10.0, 80.5]})
    out = run(df, group_fields=["g"], a_share=0.5, b_share=0.9).raise_for_error().output(0).set_index("i")
    assert out.loc["a", "ABC Class"] == "A" and out.loc["b", "ABC Class"] == "B" and out.loc["c", "ABC Class"] == "C"
    assert out.loc["f", "ABC Class"] == "A" and out.loc["f", "Rank"] == 1
    assert run(df, a_share=0.9, b_share=0.8).status == "aborted"


def test_xyz_with_zero_periods():
    rows = []
    for m in range(1, 13):
        rows.append({"i": "steady", "d": f"2025-{m:02d}-15", "v": 100.5})
        if m in (3, 9):
            rows.append({"i": "lumpy", "d": f"2025-{m:02d}-15", "v": 600.5})
    out = run(pd.DataFrame(rows), date_field="d").raise_for_error().output(0).set_index("i")
    assert out.loc["steady", "XYZ Class"] == "X" and out.loc["steady", "Coefficient Of Variation"] < 1e-9
    assert out.loc["lumpy", "XYZ Class"] == "Z" and out.loc["lumpy", "Periods"] == 12
    assert out.loc["steady", "ABC-XYZ"] in ("AX", "BX", "CX")


def test_sample_pareto_shape():
    res = run_block(HERE, SAMPLE, {"item_field": "SKU", "value_field": "Sales Value", "date_field": "Month", "xyz_field": "Units"}).raise_for_error()
    out, s = res.output(0), res.output(1).set_index("ABC Class")
    assert len(out) == out["SKU"].nunique()
    assert s.loc["A", "Share Of Items"] < 0.5 and s.loc["C", "Share Of Value"] < 0.1
    assert set(out["XYZ Class"]) <= {"X", "Y", "Z"}


def test_negative_and_text_values():
    df = pd.DataFrame({"i": ["a", "b", "c"], "v": ["100.5", "-20.5", "x"]})
    out = run(df).raise_for_error().output(0).set_index("i")
    assert out.loc["a", "ABC Class"] == "A" and out.loc["b", "ABC Class"] == "C" and out.loc["c", "ABC Class"] == "C"


def test_empty_and_bad_fields():
    res = run(pd.DataFrame({"i": pd.Series([], dtype=object), "v": pd.Series([], dtype="float64")})).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0
    assert run(pd.DataFrame({"i": ["a"], "v": [1.5]}), date_field="nope").status == "aborted"


def test_large_input_is_fast():
    n = 1_000_000
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"i": rng.integers(0, 50_000, n), "v": rng.gamma(1.5, 20, n),
                       "d": pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")})
    t0 = time.time()
    out = run(df, date_field="d").raise_for_error().output(0)
    assert time.time() - t0 < 90 and len(out) == df["i"].nunique()
