import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "store-daily-sales.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, opts)


@pytest.fixture
def small():
    return pd.DataFrame({"g": ["a", "b", "a", "a", "b"], "t": [3, 1, 1, 2, 2], "v": [30.0, 5.0, 10.0, 20.0, 15.0],
                         "name": ["x3", "y1", "x1", "x2", "y2"]})


def test_previous_change_running_total_per_group_keeps_order(small):
    out = run(small, value_fields=["v"], group_fields=["g"], sort_fields=["t"], calc_running_total=True).raise_for_error().output(0)
    assert out["t"].tolist() == [3, 1, 1, 2, 2]  # input order kept
    a = out[out.g == "a"].sort_values("t")
    assert a["v Previous"].tolist()[1:] == [10.0, 20.0] and pd.isna(a["v Previous"].iloc[0])
    assert a["v Change"].tolist()[1:] == [10.0, 10.0]
    assert a["v Running Total"].tolist() == [10.0, 30.0, 60.0]
    b = out[out.g == "b"].sort_values("t")
    assert b["v Running Total"].tolist() == [5.0, 20.0]


def test_next_and_previous_on_text_and_offset(small):
    out = run(small, value_fields=["name"], sort_fields=["g", "t"], calc_next=True, calc_change=False,
              offset=2, keep_order=False).raise_for_error().output(0)
    assert out["name"].tolist() == ["x1", "x2", "x3", "y1", "y2"]
    assert out["name Previous"].tolist()[2:] == ["x1", "x2", "x3"]
    assert out["name Next"].tolist()[:3] == ["x3", "y1", "y2"]


def test_rolling_rows_rank_share_pct(small):
    out = run(small, value_fields=["v"], group_fields=["g"], sort_fields=["t"], calc_previous=False, calc_change=False,
              calc_pct_change=True, calc_rolling_mean=True, calc_rolling_max=True, calc_rank=True, calc_share=True,
              calc_row_number=True, window=2, keep_order=False).raise_for_error().output(0)
    a = out[out.g == "a"]
    assert a["v Rolling Mean (2 rows)"].tolist() == [10.0, 15.0, 25.0]
    assert a["v Rolling Max (2 rows)"].tolist() == [10.0, 20.0, 30.0]
    assert a["v Rank"].tolist() == [3, 2, 1]
    assert np.allclose(a["v Share Of Group"], [10 / 60, 20 / 60, 30 / 60])
    assert np.allclose(a["v % Change"].tolist()[1:], [1.0, 0.5])
    assert a["Row Number"].tolist() == [1, 2, 3]


def test_full_window_leaves_early_rows_empty(small):
    out = run(small, value_fields=["v"], group_fields=["g"], sort_fields=["t"], calc_rolling_sum=True,
              window=3, full_window=True, keep_order=False).raise_for_error().output(0)
    a = out[out.g == "a"]["v Rolling Sum (3 rows)"].tolist()
    assert pd.isna(a[0]) and pd.isna(a[1]) and a[2] == 60.0


def test_rolling_days_handles_gaps():
    df = pd.DataFrame({"d": ["2025-01-01", "2025-01-02", "2025-01-05", "2025-01-09"], "v": [1.0, 2.0, 4.0, 8.0]})
    out = run(df, value_fields=["v"], sort_fields=["d"], calc_rolling_sum=True, window=3, window_unit="DAYS").raise_for_error().output(0)
    # windows: {1} {1,2} {5} (3,4 missing) {9}
    assert out["v Rolling Sum (3 days)"].tolist() == [1.0, 3.0, 4.0, 8.0]


def test_sample_store_data():
    res = run(SAMPLE, value_fields=["Sales"], group_fields=["Store"], sort_fields=["Date"], offset=7,
              calc_rolling_mean=True, window_unit="DAYS").raise_for_error()
    out = res.output(0)
    assert len(out) == 145 and "Sales Rolling Mean (7 days)" in out.columns
    gl = out[(out.Store == "Glasgow") & (out.Date == "2025-09-16")].iloc[0]
    window = out[(out.Store == "Glasgow") & (out.Date >= "2025-09-10") & (out.Date <= "2025-09-16")]["Sales"]
    assert len(window) == 5 and abs(gl["Sales Rolling Mean (7 days)"] - window.mean()) < 1e-9


def test_empty_input(small):
    res = run(small.iloc[0:0], value_fields=["v"], group_fields=["g"], sort_fields=["t"]).raise_for_error()
    assert len(res.output(0)) == 0 and "v Change" in res.output(0).columns


def test_wrong_types_text_value_field_numeric_calcs_skipped(small):
    res = run(small, value_fields=["name"], calc_running_total=True).raise_for_error()
    assert "name Running Total" not in res.output(0).columns
    assert "skipped" in res.final_message


def test_nulls_in_values_and_groups():
    df = pd.DataFrame({"g": ["a", None, "a", None], "v": pd.array([1, 2, None, 4], dtype="Int64")})
    out = run(df, value_fields=["v"], group_fields=["g"], calc_running_total=True).raise_for_error().output(0)
    assert out["v Running Total"].tolist()[1] == 2.0 and out["v Running Total"].tolist()[3] == 6.0


def test_bad_options_abort(small):
    assert run(small, value_fields=["nope"]).status == "aborted"
    assert run(small).status == "aborted"
    assert run(small, value_fields=["v"], calc_previous=False, calc_change=False).status == "aborted"
    assert run(small, value_fields=["v"], calc_rolling_mean=True, window_unit="DAYS").status == "aborted"


def test_large_input_is_fast():
    n = 300_000
    df = pd.DataFrame({"g": np.arange(n) % 500, "t": np.arange(n), "v": np.random.default_rng(1).normal(size=n)})
    t0 = time.time()
    out = run(df, value_fields=["v"], group_fields=["g"], sort_fields=["t"], calc_running_total=True,
              calc_rolling_mean=True, calc_rank=True).raise_for_error().output(0)
    assert time.time() - t0 < 60 and len(out) == n
