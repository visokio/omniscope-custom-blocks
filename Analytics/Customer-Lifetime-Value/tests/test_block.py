import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "orders.csv")
OPTS = {"customer_field": "Customer ID", "date_field": "Order Date", "value_field": "Order Value"}


def simulate(n, seed=0, r=0.6, alpha=6.0, a=0.7, b=3.0, weeks=80):
    rng = np.random.default_rng(seed)
    rows = []
    start = pd.Timestamp("2024-01-01")
    for c in range(n):
        lam, p = rng.gamma(r, 1 / alpha), rng.beta(a, b)
        t, times = 0.0, [0.0]
        while True:
            t += rng.exponential(1 / lam)
            if t > weeks:
                break
            times.append(t)
            if rng.random() < p:
                break
        for tt in times:
            rows.append((f"c{c}", start + pd.Timedelta(days=int(tt * 7)), float(rng.gamma(5, 6))))
    return pd.DataFrame(rows, columns=["Customer ID", "Order Date", "Order Value"])


def test_recovers_simulated_parameters_and_holdout():
    df = simulate(2500, seed=3)
    res = run_block(HERE, df, {**OPTS, "as_of": str((pd.Timestamp("2024-01-01") + pd.Timedelta(weeks=80)).date()), "holdout_months": 4}).raise_for_error()
    m = res.output(2).set_index("Parameter")["Value"]
    assert abs(m["r"] - 0.6) < 0.15 and abs(m["alpha"] - 6.0) < 2.0 and abs(m["a"] - 0.7) < 0.35 and abs(m["b"] - 3.0) < 1.5
    v = res.output(3).set_index("Repeat Purchases Before Holdout")
    allv = v.loc["All"]
    assert abs(allv["Predicted Purchases Per Customer"] / allv["Actual Purchases Per Customer"] - 1) < 0.25
    c = res.output(0)
    assert c["Probability Active"].between(0, 1).all() and (c["Predicted CLV"] >= 0).all()
    assert set(c["CLV Tier"]) == {"Top 10%", "Next 20%", "Middle 30%", "Bottom 40%"}


def test_recency_lowers_probability_active():
    df = simulate(800, seed=5)
    res = run_block(HERE, df, OPTS).raise_for_error()
    c = res.output(0)
    many = c[c["Purchase Days"] >= 5]
    recent = many[many["Weeks Since Last Purchase"] < 4]["Probability Active"].mean()
    old = many[many["Weeks Since Last Purchase"] > 30]["Probability Active"].mean()
    assert recent > old
    one = c[c["Purchase Days"] == 1]
    assert np.allclose(one["Probability Active"], 1.0)  # BG/NBD: no repeat purchase means no observed dropout opportunity


def test_discount_margin_and_horizon():
    df = simulate(600, seed=7)
    base = run_block(HERE, df, OPTS).raise_for_error().output(1).iloc[0]["Predicted CLV"]
    half = run_block(HERE, df, {**OPTS, "margin": 0.5}).raise_for_error().output(1).iloc[0]["Predicted CLV"]
    nodisc = run_block(HERE, df, {**OPTS, "discount_rate": 0.0}).raise_for_error().output(1).iloc[0]["Predicted CLV"]
    longer = run_block(HERE, df, {**OPTS, "horizon_months": 36}).raise_for_error().output(1).iloc[0]["Predicted CLV"]
    assert np.isclose(half, base / 2) and nodisc > base and longer > base


def test_sample_orders_groups_and_refunds():
    res = run_block(HERE, SAMPLE, {**OPTS, "group_fields": ["Acquisition Channel"]}).raise_for_error()
    s = res.output(1).set_index("Acquisition Channel")
    assert s.loc["All", "Customers"] == 3000 and np.isclose(s.drop("All")["Customers"].sum(), 3000)
    assert np.isclose(s.drop("All")["Predicted CLV"].sum(), s.loc["All", "Predicted CLV"])
    assert s.loc["Referral", "Average Predicted CLV"] > s.loc["Social", "Average Predicted CLV"]
    c = res.output(0)
    assert c["Orders"].sum() == 15849 and (c["Purchase Days"] <= c["Orders"]).all()


def test_bad_inputs_and_empty():
    df = simulate(100, seed=1)
    assert run_block(HERE, df, {**OPTS, "customer_field": "nope"}).status == "aborted"
    assert run_block(HERE, df.iloc[0:0], OPTS).status == "aborted"
    assert run_block(HERE, df.assign(**{"Order Value": "x"}), OPTS).status == "aborted"
    assert run_block(HERE, df.head(5), OPTS).status == "aborted"  # too little history
    assert run_block(HERE, df, {**OPTS, "as_of": "not a date"}).status == "aborted"
    txt = df.assign(**{"Order Date": df["Order Date"].dt.strftime("%d/%m/%Y")})
    a = run_block(HERE, txt, OPTS).raise_for_error().output(1).iloc[0]["Predicted CLV"]
    b = run_block(HERE, df, OPTS).raise_for_error().output(1).iloc[0]["Predicted CLV"]
    assert np.isclose(a, b)


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 300_000
    df = pd.DataFrame({"Customer ID": rng.integers(0, 50_000, n),
                       "Order Date": pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, 900, n), unit="D"),
                       "Order Value": rng.gamma(3, 20, n)})
    t0 = time.time()
    res = run_block(HERE, df, {**OPTS, "holdout_months": 6}).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == df["Customer ID"].nunique()
