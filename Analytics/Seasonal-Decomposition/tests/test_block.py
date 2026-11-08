import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "monthly-category-sales.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"date_field": "d", "value_field": "y", **opts})


def series(n=48, mult=False):
    months = pd.period_range("2022-01", periods=n, freq="M")
    season = np.tile(np.array([-3, -2, -1, 0, 1, 2, 3, 2, 1, 0, -1, -2], dtype=float), n // 12 + 1)[:n] + 0.5
    season -= season[:12].mean()
    trend = 100 + 2.0 * np.arange(n)
    y = trend * (1 + season / 20) if mult else trend + season
    return pd.DataFrame({"d": [p.start_time.strftime("%Y-%m-%d") for p in months], "y": y}), season


def test_additive_recovers_known_components():
    df, season = series()
    res = run(df).raise_for_error()
    comp, idx, summ = res.output(0), res.output(1), res.output(2)
    assert np.allclose(idx["Seasonal Index"].to_numpy(), season[:12], atol=1e-9)
    assert np.allclose(comp["Residual"].to_numpy()[6:-6], 0, atol=1e-9)
    assert np.allclose(comp["Trend"].to_numpy(), 100 + 2.0 * np.arange(48), atol=1e-6)  # extended ends are linear too
    assert summ["Seasonality Strength"].iloc[0] > 0.99 and summ["Peak Season"].iloc[0] == "Jul"
    assert idx["Season"].tolist()[:3] == ["Jan", "Feb", "Mar"]


def test_multiplicative_indices_average_one():
    df, _ = series(mult=True)
    idx = run(df, model="MULTIPLICATIVE").raise_for_error().output(1)
    assert abs(idx["Seasonal Index"].mean() - 1) < 1e-12 and idx["Effect"].iloc[0].endswith("vs trend")


def test_sample_groups_missing_month_and_duplicates():
    df = pd.read_csv(SAMPLE)
    df = pd.concat([df, df.iloc[[0]].assign(**{"Sales (£k)": 1.0})])  # duplicate date gets summed
    res = run_block(HERE, df, {"date_field": "Month", "value_field": "Sales (£k)", "group_fields": ["Category"]}).raise_for_error()
    summ = res.output(2).set_index("Category")
    assert summ.loc["Garden furniture", "Peak Season"] == "Jun" and summ.loc["Home heating", "Peak Season"] == "Jan"
    assert summ.loc["Kitchenware", "Interpolated Periods"] == 1
    assert len(res.output(0)) == 180


def test_quarterly_and_custom_length():
    q = pd.DataFrame({"d": [p.start_time.strftime("%Y-%m-%d") for p in pd.period_range("2020Q1", periods=16, freq="Q")],
                      "y": [10.5, 20.5, 30.5, 15.5] * 4})
    idx = run(q, frequency="QUARTER").raise_for_error().output(1)
    assert idx["Season"].tolist() == ["Q1", "Q2", "Q3", "Q4"] and idx["Seasonal Index"].idxmax() == 2
    d = pd.DataFrame({"d": pd.date_range("2025-01-06", periods=28).strftime("%Y-%m-%d"), "y": [1.5, 1.5, 1.5, 1.5, 1.5, 9.5, 9.5] * 4})
    idx = run(d, frequency="DAY").raise_for_error().output(1)
    assert idx.loc[idx["Seasonal Index"].idxmax(), "Season"] in ("Sat", "Sun")


def test_too_short_and_multiplicative_with_zero():
    df, _ = series(n=18)
    s = run(df).raise_for_error().output(2)
    assert s["Status"].iloc[0].startswith("Needs at least two full seasons")
    df2, _ = series()
    df2.loc[3, "y"] = 0.0
    assert "above zero" in run(df2, model="MULTIPLICATIVE").raise_for_error().output(2)["Status"].iloc[0]


def test_empty_and_bad_fields():
    res = run(pd.DataFrame({"d": pd.Series([], dtype=object), "y": pd.Series([], dtype="float64")})).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(2)) == 0
    assert run(series()[0], value_field="nope").status == "aborted"
    assert run(series()[0], season_length=1).status == "aborted"


def test_large_input_is_fast():
    months = pd.period_range("2000-01", periods=300, freq="M")
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"d": np.tile([p.start_time for p in months], 500), "g": np.repeat(np.arange(500), 300),
                       "y": rng.gamma(5, 10, 150_000)})
    t0 = time.time()
    res = run(df, group_fields=["g"]).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(2)) == 500
