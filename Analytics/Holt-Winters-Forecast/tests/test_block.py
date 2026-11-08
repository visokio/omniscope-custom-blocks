import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "monthly-sales.csv")


def monthly(values, start="2020-01"):
    p = pd.period_range(start, periods=len(values), freq="M")
    return pd.DataFrame({"d": p.start_time.strftime("%Y-%m-%d"), "v": values})


def run(df, **opts):
    return run_block(HERE, df, {"date_field": "d", "value_field": "v", **opts})


def fc(res):
    f = res.output(0)
    return f[f["Row Type"] == "Forecast"]


def test_pure_seasonal_pattern_is_repeated():
    pattern = np.array([10, 12, 15, 20, 30, 40, 45, 40, 30, 20, 15, 12], dtype=float)
    res = run(monthly(np.tile(pattern, 4) + 100), horizon=12).raise_for_error()
    f = fc(res)
    assert np.allclose(f["Forecast"].to_numpy(), pattern + 100, atol=1.5)
    assert res.output(1).iloc[0]["Model"].endswith(",A)") or res.output(1).iloc[0]["Model"].endswith(",M)")


def test_trend_is_extrapolated_and_flat_series_stays_flat():
    res = run(monthly(np.arange(40) * 5.0 + 50), horizon=3, seasonality="NONE").raise_for_error()
    assert np.allclose(fc(res)["Forecast"].to_numpy(), [250, 255, 260], atol=2.0)
    res = run(monthly(np.full(30, 7.0)), horizon=4).raise_for_error()
    f = fc(res)
    assert np.allclose(f["Forecast"], 7.0) and np.allclose(f["Upper 95"], 7.0)


def test_intervals_widen_and_contain_forecast():
    rng = np.random.default_rng(3)
    y = 100 + np.cumsum(rng.normal(0, 3, 60))
    f = fc(run(monthly(y), horizon=12, seasonality="NONE"))
    assert (f["Lower 95"] <= f["Lower 80"]).all() and (f["Upper 80"] <= f["Upper 95"]).all()
    width = (f["Upper 95"] - f["Lower 95"]).to_numpy()
    assert width[-1] > width[0]
    a = run(monthly(y), horizon=6, seed=5).raise_for_error().output(0)
    b = run(monthly(y), horizon=6, seed=5).raise_for_error().output(0)
    assert a.equals(b)


def test_holdout_and_forced_models():
    pattern = np.array([1, 1, 2, 3, 5, 8, 8, 5, 3, 2, 1, 1], dtype=float) * 10
    rng = np.random.default_rng(1)
    y = np.tile(pattern, 5) * (1 + rng.normal(0, 0.03, 60))
    res = run(monthly(y), holdout=12).raise_for_error()
    md = res.output(1).iloc[0]
    assert md["Holdout Periods"] == 12 and md["MASE"] < 1.5 and md["Holdout MAPE"] < 0.2
    assert (res.output(0)["Row Type"] == "Holdout forecast").sum() == 12
    forced = run(monthly(y), trend="DAMPED", seasonality="MULTIPLICATIVE").raise_for_error().output(1).iloc[0]
    assert forced["Model"] == "ETS(A,Ad,M)" and 0.8 <= forced["Phi"] <= 0.98
    neg = run(monthly(y - 30), seasonality="MULTIPLICATIVE").raise_for_error().output(1).iloc[0]
    assert not neg["Model"].endswith(",M)")  # multiplicative needs positive data


def test_series_short_history_and_aggregation():
    df = pd.concat([monthly(np.arange(36) + 10.0).assign(s="long"), monthly([5.0, 6.0]).assign(s="short")])
    res = run(df, series_fields=["s"], horizon=2).raise_for_error()
    m = res.output(1).set_index("s")
    assert m.loc["short", "Model"] == "Not fitted" and m.loc["long", "History Periods"] == 36
    lines = pd.DataFrame({"d": ["2024-01-05", "2024-01-20", "2024-03-02", "2024-04-01", "2024-05-01"], "v": [1.0, 2.0, 4.0, 5.0, 6.0]})
    a = run(lines, horizon=1).raise_for_error().output(0)
    acts = a[a["Row Type"] == "Actual"]["Actual"].tolist()
    assert acts == [3.0, 0.0, 4.0, 5.0, 6.0]  # summed per month, February filled with zero
    assert "Fewer than two seasons" in run(lines, horizon=1).raise_for_error().output(1).iloc[0]["Note"]


def test_sample_sales():
    res = run_block(HERE, SAMPLE, {"date_field": "Order Date", "value_field": "Sales", "series_fields": ["Product Line"], "holdout": 12}).raise_for_error()
    m = res.output(1).set_index("Product Line")
    assert m.loc["Gift Sets", "Model"].endswith(",M)") and m.loc["Office Paper", "Model"] == "ETS(A,N,N)"
    assert (res.output(0)["Row Type"] == "Forecast").sum() == 48


def test_bad_inputs_and_large():
    df = monthly(np.arange(30.0))
    assert run(df, date_field="zz").status == "aborted"
    assert run(df, horizon=0).status == "aborted"
    assert run(df.iloc[0:0]).raise_for_error().output(0).empty
    big = pd.concat([monthly(100 + 10 * np.sin(np.arange(96) / 12 * 2 * np.pi) + np.random.default_rng(i).normal(0, 2, 96)).assign(s=f"s{i}") for i in range(20)])
    t0 = time.time()
    res = run(big, series_fields=["s"], horizon=12).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(1)) == 20
