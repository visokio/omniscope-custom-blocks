import math
import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
DEM = os.path.join(HERE, "sample-data", "part-demand.csv")
PAR = os.path.join(HERE, "sample-data", "part-parameters.csv")
F = {"item_field": "i", "date_field": "d", "quantity_field": "q"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**F, **opts})


def weekly(vals, item="x"):
    weeks = pd.date_range("2025-01-06", periods=len(vals), freq="W-MON")
    return pd.DataFrame({"i": item, "d": weeks.strftime("%Y-%m-%d"), "q": vals}).query("q > 0")


def test_formulas_and_zero_weeks():
    stats = pytest.importorskip("scipy.stats")
    vals = [10, 0, 20, 10, 0, 20, 0, 10]  # history runs to the latest period with any demand
    r = run(weekly(vals), lead_time=2, service_level=0.95).raise_for_error().output(0).iloc[0]
    m, sd = np.mean(vals), np.std(vals, ddof=1)
    z = stats.norm.ppf(0.95)
    assert r["Periods Of History"] == 8 and np.isclose(r["Average Demand"], m) and np.isclose(r["Demand Std Dev"], sd)
    assert abs(r["Z"] - z) < 1e-8 and np.isclose(r["Safety Stock"], z * sd * math.sqrt(2), atol=1e-6)
    assert np.isclose(r["Reorder Point"], m * 2 + r["Safety Stock"])


def test_lead_time_variability_eoq_and_reorder_list():
    d = weekly([10, 12, 8, 10, 11, 9, 10, 10])
    p = pd.DataFrame({"pi": ["x"], "lt": [3.0], "ltsd": [1.0], "cost": [20.0], "stock": [5.0]})
    res = run([d, p], param_item_field="pi", param_lead_field="lt", param_lead_sd_field="ltsd", param_cost_field="cost",
              param_stock_field="stock", ordering_cost=50, holding_rate=0.25).raise_for_error()
    r = res.output(0).iloc[0]
    mean, sd = 10.0, np.std([10, 12, 8, 10, 11, 9, 10, 10], ddof=1)
    assert np.isclose(r["Safety Stock"], r["Z"] * math.sqrt(3 * sd ** 2 + mean ** 2 * 1.0), atol=1e-6)
    assert np.isclose(r["EOQ"], math.sqrt(2 * mean * 52 * 50 / (0.25 * 20)))
    assert r["Status"] == "Below reorder point" and np.isclose(r["Suggested Order"], r["Order-Up-To Level"] - 5)
    assert len(res.output(1)) == 1


def test_service_level_monotonic_and_override():
    d = weekly([5, 15, 10, 0, 20, 10, 5, 15])
    s90 = run(d, service_level=0.90).raise_for_error().output(0).iloc[0]["Safety Stock"]
    s99 = run(d, service_level=0.99).raise_for_error().output(0).iloc[0]["Safety Stock"]
    assert s99 > s90
    p = pd.DataFrame({"pi": ["x"], "sl": [0.99]})
    o = run([d, p], service_level=0.90, param_item_field="pi", param_service_field="sl").raise_for_error().output(0).iloc[0]
    assert np.isclose(o["Safety Stock"], s99)


def test_sample_data():
    res = run_block(HERE, [DEM, PAR], {"item_field": "Part Number", "date_field": "Order Date", "quantity_field": "Quantity",
                                       "param_item_field": "Part Number", "param_lead_field": "Lead Time (weeks)",
                                       "param_lead_sd_field": "Lead Time Std Dev (weeks)", "param_cost_field": "Unit Cost",
                                       "param_stock_field": "Stock On Hand", "param_service_field": "Target Service Level",
                                       "ordering_cost": 40}).raise_for_error()
    lv = res.output(0)
    assert len(lv) == 25 and (lv["Reorder Point"] >= lv["Safety Stock"]).all() and lv["EOQ"].notna().all()
    assert (lv["Service Level"].isin([0.95, 0.98])).all()


def test_bad_inputs():
    d = weekly([1, 2, 3])
    assert run(d, service_level=0.3).status == "aborted"
    assert run(d, quantity_field="nope").status == "aborted"
    assert run([d, pd.DataFrame({"x": [1]})]).status == "aborted"  # parameters without item field
    res = run(d.iloc[0:0]).raise_for_error()
    assert len(res.output(0)) == 0


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 500_000
    df = pd.DataFrame({"i": rng.integers(0, 5000, n), "d": pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D"),
                       "q": rng.integers(1, 10, n)})
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == df["i"].nunique()
