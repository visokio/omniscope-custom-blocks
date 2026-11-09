import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "property-listings.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, opts)


@pytest.fixture
def df():
    return pd.DataFrame({"g": ["a", "a", "a", "b", "b", "c"],
                         "t": [1, 2, 3, 1, 2, 1],
                         "x": [1.5, np.nan, 5.5, 10.5, np.nan, np.nan],
                         "n": pd.array([2, None, 4, 7, None, 1], dtype="Int64"),
                         "s": ["p", None, "p", "q", "r", None]})


def test_median_overall_and_flags(df):
    res = run(df, fields=["x"]).raise_for_error()
    out = res.output(0)
    assert out["x"].tolist() == [1.5, 5.5, 5.5, 10.5, 5.5, 5.5]
    assert out["x Was Imputed"].tolist() == [0, 1, 0, 0, 1, 1]
    rep = res.output(1).set_index("Field")
    assert rep.loc["x", "Missing Before"] == 3 and rep.loc["x", "Value Used"] == "5.5"


def test_group_mean_with_fallback(df):
    out = run(df, fields=["x"], numeric_method="MEAN", group_fields=["g"]).raise_for_error().output(0)
    assert out["x"].tolist()[1] == 3.5 and out["x"].tolist()[4] == 10.5
    assert abs(out["x"].tolist()[5] - 17.5 / 3) < 1e-9  # group c has no values: overall mean
    out = run(df, fields=["x"], numeric_method="MEAN", group_fields=["g"], fallback_overall=False).raise_for_error().output(0)
    assert pd.isna(out["x"].iloc[5])


def test_integer_fields_stay_integer(df):
    out = run(df, fields=["n"], numeric_method="MEAN").raise_for_error().output(0)
    assert out["n"].dtype == "Int64" and out["n"].tolist()[1] == 4  # mean 3.5 -> 4


def test_text_mode_and_constant(df):
    assert run(df, fields=["s"]).raise_for_error().output(0)["s"].tolist() == ["p", "p", "p", "q", "r", "p"]
    out = run(df, fields=["s"], text_method="CONSTANT", constant_text="Unknown").raise_for_error().output(0)
    assert out["s"].tolist()[1] == "Unknown"


def test_previous_next_interpolate_in_order_within_groups(df):
    shuffled = df.iloc[[2, 0, 1, 4, 3, 5]].reset_index(drop=True)
    out = run(shuffled, fields=["x"], numeric_method="FFILL", group_fields=["g"], order_fields=["t"]).raise_for_error().output(0)
    a = out[out.g == "a"].sort_values("t")["x"].tolist()
    assert a == [1.5, 1.5, 5.5]
    out = run(shuffled, fields=["x"], numeric_method="INTERPOLATE", group_fields=["g"], order_fields=["t"]).raise_for_error().output(0)
    assert out[out.g == "a"].sort_values("t")["x"].tolist() == [1.5, 3.5, 5.5]
    assert out[out.g == "b"].sort_values("t")["x"].tolist() == [10.5, 10.5]  # edge: nearest value fall-back
    out = run(shuffled, fields=["x"], numeric_method="BFILL", group_fields=["g"], order_fields=["t"], fallback_overall=False).raise_for_error().output(0)
    assert out[out.g == "a"].sort_values("t")["x"].tolist() == [1.5, 5.5, 5.5]


def test_sentinels_count_as_missing():
    d = pd.DataFrame({"v": [10.5, -999.0, 30.5], "s": ["x", "unknown", "x"]})
    out = run(d, extra_missing="-999, unknown").raise_for_error().output(0)
    assert out["v"].tolist() == [10.5, 20.5, 30.5] and out["s"].tolist() == ["x", "x", "x"]


def test_sample_group_median():
    res = run(SAMPLE, fields=["Bedrooms", "Floor Area (sqm)", "Agent"], group_fields=["Property Type", "Region"],
              extra_missing="-999").raise_for_error()
    out = res.output(0)
    assert out[["Bedrooms", "Floor Area (sqm)", "Agent"]].isna().sum().sum() == 0
    assert (out["Floor Area (sqm)"] > 0).all()
    assert res.output(1).set_index("Field").loc["Floor Area (sqm)", "Imputed"] == 13


def test_empty_input(df):
    res = run(df.iloc[0:0]).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) >= 1


def test_wrong_types_dates_ignored_and_unknown_field_aborts(df):
    d = df.assign(when=pd.to_datetime(["2025-01-01", None, None, None, None, None]))
    out = run(d).raise_for_error().output(0)
    assert out["when"].isna().sum() == 5  # dates are left alone
    assert run(df, fields=["nope"]).status == "aborted"


def test_leave_missing_method(df):
    out = run(df, fields=["x"], numeric_method="NONE").raise_for_error().output(0)
    assert out["x"].isna().sum() == 3 and "x Was Imputed" not in out.columns


def test_large_input_is_fast():
    n = 300_000
    rng = np.random.default_rng(2)
    x = rng.normal(size=n)
    x[rng.random(n) < 0.2] = np.nan
    d = pd.DataFrame({"g": rng.integers(0, 200, n), "x": x, "t": np.arange(n)})
    t0 = time.time()
    out = run(d, fields=["x"], group_fields=["g"]).raise_for_error().output(0)
    out2 = run(d, fields=["x"], numeric_method="INTERPOLATE", group_fields=["g"], order_fields=["t"]).raise_for_error().output(0)
    assert time.time() - t0 < 60 and out["x"].isna().sum() == 0 and len(out2) == n
