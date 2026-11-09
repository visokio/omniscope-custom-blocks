import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "monthly-budget.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, opts)


def wide():
    return pd.DataFrame({"name": [" a ", "b"], "Jan 2025": [10.5, 20.5], "Feb 2025": [30.5, None], "Mar 2025": [59.0, 79.5], "n": pd.array([1, 2], dtype="Int64")})


def test_pattern_selection_row_share_and_row_stats():
    out = run(wide(), field_pattern="2025$", operation="ROW_SHARE", output="ADD", suffix=" %", row_sum=True, row_count=True).raise_for_error().output(0)
    assert abs(out["Jan 2025 %"].iloc[0] - 0.105) < 1e-12 and abs(out["Mar 2025 %"].iloc[1] - 79.5 / 100) < 1e-12
    assert out["Jan 2025"].iloc[0] == 10.5  # originals kept
    assert np.isclose(out["Row Sum"].iloc[0], 1.0) and out["Row Count"].tolist() == [3, 2]


def test_index_to_base_and_diff():
    out = run(wide(), field_pattern="2025$", operation="INDEX_TO_BASE", base_field="Jan 2025").raise_for_error().output(0)
    assert out["Jan 2025"].tolist() == [100.0, 100.0] and np.isclose(out["Mar 2025"].iloc[0], 59 / 10.5 * 100)
    d = run(wide(), fields=["Mar 2025"], operation="DIFF_FROM_BASE", base_field="Jan 2025").raise_for_error().output(0)
    assert d["Mar 2025"].tolist() == [48.5, 59.0]
    assert run(wide(), field_pattern="2025$", operation="INDEX_TO_BASE").status == "aborted"


def test_arithmetic_round_fill_keeps_integers():
    out = run(wide(), type_filter="NUMBER", operation="FILL", value=0).raise_for_error().output(0)
    assert out["Feb 2025"].tolist() == [30.5, 0.0] and out["n"].dtype == "Int64"
    r = run(wide(), field_pattern="2025$", operation="ROUND", decimals=0).raise_for_error().output(0)
    assert r["Jan 2025"].tolist() == [10.0, 20.0]
    m = run(wide(), field_pattern="2025$", operation="MULTIPLY", value=1.2).raise_for_error().output(0)
    assert np.isclose(m["Jan 2025"].iloc[0], 12.6)


def test_scaling_ops():
    z = run(wide(), fields=["Jan 2025"], operation="ZSCORE").raise_for_error().output(0)
    assert np.isclose(z["Jan 2025"].sum(), 0)
    mm = run(wide(), fields=["Mar 2025"], operation="MINMAX").raise_for_error().output(0)
    assert mm["Mar 2025"].tolist() == [0.0, 1.0]
    cs = run(wide(), fields=["Jan 2025"], operation="COLUMN_SHARE").raise_for_error().output(0)
    assert np.isclose(cs["Jan 2025"].sum(), 1)


def test_text_ops_and_type_skipping():
    t = run(wide(), fields=["name", "n"], operation="TRIM").raise_for_error()
    assert t.output(0)["name"].tolist() == ["a", "b"] and "skipped" in t.final_message
    p = run(wide(), fields=["name"], operation="PREFIX", text_value="Dept: ", output="ADD").raise_for_error().output(0)
    assert p["name (new)"].iloc[1] == "Dept: b"
    n = run(pd.DataFrame({"x": ["1", "2", "x"]}), fields=["x"], operation="TO_NUMBER").raise_for_error().output(0)
    assert n["x"].dtype == "Int64" and pd.isna(n["x"].iloc[2])


def test_sample_budget():
    out = run(SAMPLE, field_pattern="2025$", operation="ROW_SHARE", output="ADD", suffix=" share", row_sum=True).raise_for_error().output(0)
    shares = out[[c for c in out.columns if c.endswith(" share")]]
    assert shares.shape[1] == 12 and np.allclose(shares.sum(axis=1), 1)


def test_bad_options_and_empty():
    assert run(wide(), fields=["nope"], operation="ROUND").status == "aborted"
    assert run(wide(), field_pattern="(", operation="ROUND").status == "aborted"
    assert run(wide(), field_pattern="zzz", operation="ROUND").status == "aborted"
    res = run(wide().iloc[0:0], field_pattern="2025$", operation="ROUND", row_mean=True).raise_for_error()
    assert len(res.output(0)) == 0


def test_large_input_is_fast():
    df = pd.DataFrame(np.random.default_rng(0).normal(size=(200_000, 24)), columns=[f"m{i}" for i in range(24)])
    t0 = time.time()
    out = run(df, field_pattern="^m", operation="ROW_SHARE", output="ADD", row_sum=True, row_std=True).raise_for_error().output(0)
    assert time.time() - t0 < 60 and out.shape[1] == 24 * 2 + 2
