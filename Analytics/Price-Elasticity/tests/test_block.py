import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "weekly-price-volume.csv")
F = {"price_field": "p", "volume_field": "q"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**F, **opts})


def synthetic(e=-1.5, n=60, noise=0.0, seed=0, promo_lift=0.0):
    rng = np.random.default_rng(seed)
    p = rng.uniform(1, 3, n)
    promo = (rng.random(n) < 0.3).astype(float)
    q = 500 * p ** e * np.exp(promo_lift * promo) * np.exp(rng.normal(0, noise, n)) if noise else 500 * p ** e * np.exp(promo_lift * promo)
    return pd.DataFrame({"p": p, "q": q, "promo": promo})


def test_recovers_exact_elasticity_and_effects():
    r = run(synthetic(-1.5)).raise_for_error().output(0).iloc[0]
    assert abs(r["Elasticity"] + 1.5) < 1e-9 and r["R Squared"] > 0.999999
    assert abs(r["Volume Change For +5% Price"] - (1.05 ** -1.5 - 1)) < 1e-9
    assert r["Interpretation"].startswith("Elastic")


def test_control_removes_promotion_bias():
    df = synthetic(-0.8, noise=0.02, promo_lift=0.4)
    df.loc[df.promo == 1, "p"] *= 0.8  # promotions are price cuts too
    biased = run(df).raise_for_error().output(0).iloc[0]["Elasticity"]
    fixed = run(df, control_fields=["promo"]).raise_for_error().output(0).iloc[0]["Elasticity"]
    assert abs(fixed + 0.8) < 0.05 and abs(biased + 0.8) > abs(fixed + 0.8)


def test_p_value_and_ci_match_scipy():
    stats = pytest.importorskip("scipy.stats")
    df = synthetic(-0.6, noise=0.15, seed=3)
    r = run(df).raise_for_error().output(0).iloc[0]
    ref = stats.linregress(np.log(df.p), np.log(df.q))
    assert abs(r["Elasticity"] - ref.slope) < 1e-9 and abs(r["Standard Error"] - ref.stderr) < 1e-9
    assert abs(r["P Value"] - ref.pvalue) < 1e-9
    crit = stats.t.ppf(0.975, len(df) - 2)
    assert abs(r["CI Low"] - (ref.slope - crit * ref.stderr)) < 1e-6


def test_groups_curves_and_sample():
    res = run_block(HERE, SAMPLE, {"price_field": "Average Price", "volume_field": "Units Sold", "group_fields": ["Product"],
                                   "control_fields": ["On Promotion"]}).raise_for_error()
    e = res.output(0).set_index("Product")["Elasticity"]
    assert e["Chocolate bar"] < -1.8 and -1.0 < e["Toilet roll 9-pack"] < -0.3
    c = res.output(1)
    assert len(c) == 6 * 25 and (c["Predicted Volume"] > 0).all()
    assert res.output(2)["Fitted Volume"].notna().all()


def test_degenerate_cases():
    flat = pd.DataFrame({"p": [2.0] * 20, "q": np.arange(1, 21, dtype=float)})
    assert "never changes" in run(flat).raise_for_error().output(0)["Status"].iloc[0]
    few = synthetic(n=5)
    assert run(few).raise_for_error().output(0)["Status"].iloc[0].startswith("Too few")
    bad = synthetic().assign(q=0.0)
    assert run(bad).raise_for_error().output(0)["Status"].iloc[0].startswith("Too few")
    pos = pd.DataFrame({"p": np.linspace(1, 3, 30), "q": np.linspace(10, 40, 30)})
    assert "confounding" in run(pos).raise_for_error().output(0)["Interpretation"].iloc[0]


def test_bad_options_and_empty():
    assert run(synthetic(), price_field="nope").status == "aborted"
    assert run(synthetic(), control_fields=["p"]).status == "aborted"
    res = run(synthetic().iloc[0:0]).raise_for_error()
    assert res.output(0)["Status"].iloc[0].startswith("Too few")


def test_large_input_is_fast():
    rng = np.random.default_rng(1)
    n = 500_000
    df = pd.DataFrame({"g": rng.integers(0, 2000, n), "p": rng.uniform(1, 5, n)})
    df["q"] = 100 * df["p"] ** -1.2 * rng.lognormal(0, 0.1, n)
    t0 = time.time()
    res = run(df, group_fields=["g"]).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == 2000
