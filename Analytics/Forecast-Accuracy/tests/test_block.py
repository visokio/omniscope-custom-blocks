import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "weekly-forecasts.csv")
F = {"actual_field": "a", "forecast_fields": ["f1", "f2"], "item_fields": ["i"], "period_field": "p"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**F, **opts})


def data():
    return pd.DataFrame({"i": ["x"] * 4 + ["y"] * 4, "p": [1, 2, 3, 4] * 2,
                         "a": [10.5, 20.5, 0.0, 40.5, 5.5, 5.5, 5.5, 5.5],
                         "f1": [12.5, 18.5, 1.0, 40.5, 5.5, 6.5, 4.5, 5.5],
                         "f2": [20.5, 30.5, 10.0, 50.5, 9.5, 9.5, 9.5, 9.5]})


def test_metrics_by_hand():
    res = run(data()).raise_for_error()
    it = res.output(0).set_index(["i", "Model"])
    x1 = it.loc[("x", "f1")]
    e = np.array([2, -2, 1, 0])
    assert np.isclose(x1["MAE"], np.abs(e).mean()) and np.isclose(x1["RMSE"], np.sqrt((e ** 2).mean()))
    assert np.isclose(x1["MAPE"], np.mean([2 / 10.5, 2 / 20.5, 0 / 40.5]))  # actual 0 excluded
    assert np.isclose(x1["WAPE"], 5 / 71.5) and np.isclose(x1["Bias"], 1 / 71.5)
    assert it.loc[("x", "f1"), "Best Model For Item"] == "Yes" and it.loc[("x", "f2"), "Best Model For Item"] == "No"
    assert "Over-forecasting" in it.loc[("y", "f2"), "Flags"]


def test_tracking_signal_and_overall_ranking():
    res = run(data()).raise_for_error()
    it = res.output(0).set_index(["i", "Model"])
    assert np.isclose(it.loc[("y", "f2"), "Tracking Signal"], 16 / 4)  # all errors +4
    ov = res.output(1).set_index("Model")
    assert ov.loc["f1", "Rank"] == 1 and ov.loc["f1", "Items Where Best"] == 2
    assert len(res.output(2)) == 16


def test_sample_models():
    res = run_block(HERE, SAMPLE, {"actual_field": "Actual Units", "forecast_fields": ["Statistical Forecast", "Sales Team Forecast", "Naive Forecast"],
                                   "item_fields": ["SKU"], "period_field": "Week"}).raise_for_error()
    ov = res.output(1).set_index("Model")
    assert ov.loc["Statistical Forecast", "Rank"] == 1 and ov.loc["Sales Team Forecast", "Bias"] > 0.1
    it = res.output(0)
    assert it[it.Model == "Sales Team Forecast"]["Flags"].str.contains("Over").mean() > 0.5


def test_no_items_and_missing_values():
    d = data().drop(columns=["i"])
    d.loc[0, "f1"] = None
    res = run(d, item_fields=[]).raise_for_error()
    assert len(res.output(0)) == 2 and res.output(0).set_index("Model").loc["f1", "Periods"] == 7


def test_bad_options_and_empty():
    assert run(data(), forecast_fields=[]).status == "aborted"
    assert run(data(), forecast_fields=["a"]).status == "aborted"
    assert run(data(), actual_field="nope").status == "aborted"
    res = run(data().iloc[0:0]).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(2)) == 0


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 500_000
    df = pd.DataFrame({"i": rng.integers(0, 10_000, n), "p": rng.integers(0, 52, n), "a": rng.gamma(2, 50, n)})
    df["f1"] = df["a"] * rng.normal(1, 0.1, n)
    df["f2"] = df["a"] * rng.normal(1.1, 0.2, n)
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == 2 * df["i"].nunique()
