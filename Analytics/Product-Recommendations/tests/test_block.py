import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "purchases.csv")


def run(df, **opts):
    return run_block(HERE, df, {"customer_field": "c", "product_field": "p", **opts})


def toy():
    rows = [(f"u{i}", "tea") for i in range(10)] + [(f"u{i}", "teapot") for i in range(8)] + [(f"u{i}", "coffee") for i in range(8, 20)] + \
           [(f"u{i}", "grinder") for i in range(12, 20)] + [("u0", "tea")]
    return pd.DataFrame(rows, columns=["c", "p"])


def test_cosine_similarity_and_recommendations():
    res = run(toy(), min_customers=1, shrinkage=0).raise_for_error()
    s = res.output(1)
    tt = s[(s["Product"] == "tea") & (s["Similar Product"] == "teapot")].iloc[0]
    assert np.isclose(tt["Similarity"], 8 / np.sqrt(10 * 8)) and tt["Customers Who Bought Both"] == 8 and tt["Rank"] == 1
    r = res.output(0)
    u9 = r[r["c"] == "u9"]
    assert u9.iloc[0]["Recommended Product"] == "teapot" and u9.iloc[0]["Because You Bought"] == "tea"
    assert not ((r["c"] == "u0") & (r["Recommended Product"].isin(["tea", "teapot"]))).any()  # already bought


def test_options():
    df = toy()
    assert run(df, min_customers=1, top_n=1).raise_for_error().output(0)["Rank"].max() == 1
    inc = run(df, min_customers=1, exclude_bought=False).raise_for_error().output(0)
    assert ((inc["c"] == "u0") & (inc["Recommended Product"] == "teapot")).any()
    small = run(df, min_customers=9).raise_for_error()
    assert set(small.output(1)["Product"]) <= {"tea", "coffee"} and small.output(2)["Products Left Out (too few customers)"].iloc[0] == 2
    a = run(df, min_customers=1, shrinkage=0).raise_for_error().output(1)["Similarity"].max()
    b = run(df, min_customers=1, shrinkage=50).raise_for_error().output(1)["Similarity"].max()
    assert b < a


def test_sample_purchases():
    res = run_block(HERE, SAMPLE, {"customer_field": "Customer ID", "product_field": "Product"}).raise_for_error()
    s = res.output(1)
    top = s[(s["Product"] == "Bread Flour") & (s["Rank"] <= 5)]["Similar Product"]
    assert set(top) <= {"Dried Yeast", "Bread Tin", "Sourdough Starter Kit", "Proving Basket", "Rye Flour"}
    assert res.output(2)["Products Left Out (too few customers)"].iloc[0] == 1


def test_coverage_products_add_up():
    """Products counts every product in the data, and equals Products Scored + Products Left Out (it counted only
    the products kept, so next to Products Left Out it read as one product short of the data's total)."""
    df = toy()
    cov = run(df, min_customers=9).raise_for_error().output(2).iloc[0]
    assert cov["Products"] == df.iloc[:, 1].nunique()
    assert cov["Products"] == cov["Products Scored"] + cov["Products Left Out (too few customers)"]
    assert cov["Products Left Out (too few customers)"] == 2
    res = run_block(HERE, SAMPLE, {"customer_field": "Customer ID", "product_field": "Product"}).raise_for_error()
    cov = res.output(2).iloc[0]
    assert (cov["Products"], cov["Products Scored"], cov["Products Left Out (too few customers)"]) == (31, 30, 1)


def test_bad_inputs_and_large():
    assert run(toy(), customer_field="zz").status == "aborted"
    assert len(run(toy().iloc[0:0]).raise_for_error().output(0)) == 0
    rng = np.random.default_rng(0)
    big = pd.DataFrame({"c": rng.integers(0, 40_000, 400_000), "p": rng.integers(0, 1500, 400_000)})
    t0 = time.time()
    res = run(big).raise_for_error()
    assert time.time() - t0 < 120 and res.output(0)["c"].nunique() > 39_000
