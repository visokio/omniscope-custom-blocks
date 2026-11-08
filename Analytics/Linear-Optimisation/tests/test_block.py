import os
import time

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("scipy")
from harness.runner import run_block  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
PRODUCTS = os.path.join(HERE, "sample-data", "products.csv")
RESOURCES = os.path.join(HERE, "sample-data", "resource-usage.csv")
F = {"var_name_field": "v", "objective_field": "c", "constraint_field": "k", "constraint_var_field": "v",
     "coefficient_field": "a", "sense_field": "s", "limit_field": "b"}
DEMO = {"var_name_field": "Product", "objective_field": "Profit Per Unit", "lower_field": "Minimum Units", "upper_field": "Maximum Demand",
        "integer_field": "Whole Units", "constraint_field": "Resource", "constraint_var_field": "Product",
        "coefficient_field": "Usage Per Unit", "sense_field": "Sense", "limit_field": "Capacity"}


def run(v, c, **opts):
    return run_block(HERE, [v, c], {**F, **opts})


def textbook():
    v = pd.DataFrame({"v": ["x", "y"], "c": [3.0, 5.0]})
    c = pd.DataFrame({"k": ["m1", "m2", "m3", "m3"], "v": ["x", "y", "x", "y"], "a": [1.0, 2.0, 3.0, 2.0],
                      "s": ["<=", "<=", "<=", "<="], "b": [4.0, 12.0, 18.0, 18.0]})
    return v, c


def test_textbook_lp_values_and_shadow_prices():
    res = run(*textbook()).raise_for_error()
    sol = res.output(0).set_index("v")
    assert np.allclose(sol["Optimal Value"], [2.0, 6.0])
    cons = res.output(1).set_index("Constraint")
    assert np.allclose(cons["Shadow Price"], [0.0, 1.5, 1.0])
    assert cons["Binding"].tolist() == ["No", "Yes", "Yes"] and np.isclose(cons.loc["m1", "Slack"], 2.0)
    assert np.isclose(res.output(2)["Objective Value"].iloc[0], 36.0) and res.output(2)["Status"].iloc[0] == "Optimal"


def test_minimise_with_ge_and_eq():
    v = pd.DataFrame({"v": ["a", "b"], "c": [2.0, 3.0]})
    c = pd.DataFrame({"k": ["need", "need", "mix", "mix"], "v": ["a", "b", "a", "b"], "a": [1.0, 1.0, 1.0, -1.0],
                      "s": [">=", ">=", "=", "="], "b": [10.0, 10.0, 2.0, 2.0]})
    res = run(v, c, objective_sense="MINIMISE").raise_for_error()
    sol = res.output(0).set_index("v")["Optimal Value"]
    assert np.isclose(sol["a"], 6.0) and np.isclose(sol["b"], 4.0)
    sp = res.output(1).set_index("Constraint")["Shadow Price"]
    assert np.isclose(sp["need"], 2.5)  # one more unit needed costs 2.5


def test_integer_sample_respects_bounds_and_capacity():
    res = run_block(HERE, [PRODUCTS, RESOURCES], DEMO).raise_for_error()
    sol, cons, summ = res.output(0), res.output(1), res.output(2)
    assert summ["Status"].iloc[0] == "Optimal" and summ["Integer Variables"].iloc[0] == 5
    x = sol["Optimal Value"]
    assert (x == x.round()).all() and (x >= sol["Minimum Units"]).all() and (x <= sol["Maximum Demand"]).all()
    assert (cons["Used"] <= cons["Limit"] + 1e-6)[cons["Sense"] == "<="].all()
    s = sol.set_index("Product")["Optimal Value"]
    assert s["Chair"] >= 4 * s["Dining Table"]


def test_infeasible_and_unbounded():
    v = pd.DataFrame({"v": ["x"], "c": [1.0]})
    inf = pd.DataFrame({"k": ["a", "b"], "v": ["x", "x"], "a": [1.0, 1.0], "s": ["<=", ">="], "b": [1.0, 2.0]})
    assert run(v, inf).raise_for_error().output(2)["Status"].iloc[0] == "Infeasible"
    unb = pd.DataFrame({"k": ["a"], "v": ["x"], "a": [1.0], "s": [">="], "b": [1.0]})
    assert run(v, unb).raise_for_error().output(2)["Status"].iloc[0] == "Unbounded"


def test_bad_models_abort():
    v, c = textbook()
    assert run(v, c.assign(v=["x", "y", "x", "z"])).status == "aborted"  # unknown variable
    assert run(v, c.assign(s=["<=", "<=", "~", "~"])).status == "aborted"
    assert run(pd.concat([v, v]), c).status == "aborted"  # duplicate names
    assert run(v.assign(c=["x", "5"]), c).status == "aborted"
    assert run_block(HERE, [v], F).status == "aborted"


def test_empty_variables_abort():
    v = pd.DataFrame({"v": pd.Series([], dtype=object), "c": pd.Series([], dtype="float64")})
    assert run(v, textbook()[1].iloc[0:0]).status == "aborted"


def test_large_lp_is_fast():
    rng = np.random.default_rng(0)
    nv, nc = 2000, 300
    v = pd.DataFrame({"v": [f"p{i}" for i in range(nv)], "c": rng.uniform(1, 10, nv), "u": 100.0})
    rows = [{"k": f"r{k}", "v": f"p{i}", "a": float(rng.uniform(0.1, 2)), "s": "<=", "b": 5000.0}
            for k in range(nc) for i in rng.choice(nv, 40, replace=False)]
    t0 = time.time()
    res = run(v, pd.DataFrame(rows), upper_field="u").raise_for_error()
    assert time.time() - t0 < 60 and res.output(2)["Status"].iloc[0] == "Optimal"
