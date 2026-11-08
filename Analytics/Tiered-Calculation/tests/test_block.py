import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SALES = os.path.join(HERE, "sample-data", "quarterly-sales.csv")
PLANS = os.path.join(HERE, "sample-data", "commission-plans.csv")
TIERS = "0-10000: 0, 10000-50000: 20%, 50000-: 0.4"


def run(df, *more, **opts):
    return run_block(HERE, [df, *more] if more else df, {"amount_field": "a", **opts})


def test_marginal_bands():
    o = run(pd.DataFrame({"a": [5000.0, 30000, 80000, 50000]}), tiers=TIERS).raise_for_error()
    r = o.output(0)
    assert r["Tiered Result"].tolist() == [0.0, 4000.0, 8000 + 12000, 8000.0]
    assert np.isclose(r["Effective Rate"].iloc[2], 20000 / 80000) and r["Tier Reached"].iloc[2] == "50,000 and over"
    b = o.output(1)
    assert b[b["Row Number"] == 3]["Result In Tier"].tolist() == [0.0, 8000.0, 12000.0]


def test_whole_amount_with_fixed_and_plans():
    r = run(pd.DataFrame({"a": [500.0, 1500, 6000]}), tiers="0-1000: 0, 1000-5000: 0.05 + 10, 5000-: 0.1 + 20", mode="WHOLE").raise_for_error().output(0)
    assert r["Tiered Result"].tolist() == [0.0, 85.0, 620.0]
    t = pd.DataFrame({"p": ["x", "x", "y"], "f": [0, 100, 0], "t": [100, None, None], "r": ["1%", "2%", "10%"]})
    d = pd.DataFrame({"a": [150.0, 150.0, 150.0], "k": ["x", "y", "z"]})
    res = run(d, t, plan_field="k", tier_plan_field="p", tier_from_field="f", tier_to_field="t", tier_rate_field="r").raise_for_error()
    o = res.output(0)
    assert np.isclose(o["Tiered Result"].iloc[0], 1 + 1) and np.isclose(o["Tiered Result"].iloc[1], 15) and pd.isna(o["Tiered Result"].iloc[2])
    assert "no tiers for plan" in res.final_message


def test_sample_and_bad_tiers():
    res = run_block(HERE, [SALES, PLANS], {"amount_field": "Sales (GBP)", "plan_field": "Plan", "tier_plan_field": "Plan", "tier_from_field": "From",
                                           "tier_to_field": "To", "tier_rate_field": "Rate"}).raise_for_error()
    o = res.output(0)
    assert o["Tiered Result"].notna().all() and (o["Effective Rate"] <= 0.10 + 1e-12).all()
    assert run(pd.DataFrame({"a": [1.0]}), tiers="").status == "aborted"
    assert run(pd.DataFrame({"a": [1.0]}), tiers="cheap: 0.1").status == "aborted"
    assert run(pd.DataFrame({"a": [1.0]}), tiers="0-100: 0.1, 50-200: 0.2").status == "aborted"
    assert run(pd.DataFrame({"a": [1.0]}), tiers="100-50: 0.1").status == "aborted"
    assert run(pd.DataFrame({"a": ["x", None]}), tiers=TIERS).raise_for_error().output(0)["Tiered Result"].isna().all()


def test_large_input_is_fast():
    big = pd.DataFrame({"a": np.random.default_rng(0).gamma(2, 30000, 100_000)})
    t0 = time.time()
    run(big, tiers=TIERS).raise_for_error()
    assert time.time() - t0 < 120
