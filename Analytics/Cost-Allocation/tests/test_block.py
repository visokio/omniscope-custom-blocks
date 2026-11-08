import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
POOLS = os.path.join(HERE, "sample-data", "cost-pools.csv")
DRV = os.path.join(HERE, "sample-data", "drivers.csv")
O = {"pool_field": "p", "amount_field": "a", "pool_driver_field": "d", "receiver_field": "r", "driver_field": "d", "value_field": "v"}


def run(pools, drivers, **opts):
    return run_block(HERE, [pools, drivers], {**O, **opts})


def test_penny_exact_split():
    pools = pd.DataFrame({"p": ["x"], "a": [100.0], "d": ["heads"]})
    drv = pd.DataFrame({"r": ["A", "B", "C"], "d": ["heads"] * 3, "v": [1, 1, 1]})
    a = run(pools, drv).raise_for_error().output(0)
    assert sorted(a["Allocated"].tolist()) == [33.33, 33.33, 33.34] and np.isclose(a["Allocated"].sum(), 100.0)
    assert np.allclose(a["Share"], 1 / 3)


def test_multiple_pools_wide_form_default_driver():
    pools = pd.DataFrame({"p": ["it", "fac", "misc"], "a": [1000.0, 999.99, 50.0], "d": ["users", "area", None]})
    wide = pd.DataFrame({"r": ["A", "B"], "users": [3, 1], "area": [100.0, 300.0]})
    res = run_block(HERE, [pools, wide], {"pool_field": "p", "amount_field": "a", "pool_driver_field": "d", "receiver_field": "r", "default_driver": "users"}).raise_for_error()
    a = res.output(0)
    assert np.isclose(a[a["Pool"] == "fac"]["Allocated"].sum(), 999.99) and a[(a["Pool"] == "it") & (a["r"] == "A")]["Allocated"].iloc[0] == 750.0
    assert np.isclose(a[a["Pool"] == "misc"]["Allocated"].sum(), 50.0)  # default driver used
    r = res.output(1).set_index("r")
    assert np.isclose(r["Total Allocated"].sum(), 2049.99) and np.isclose(r["Share Of All Costs"].sum(), 1.0)


def test_unallocated_and_bad_inputs():
    pools = pd.DataFrame({"p": ["x", "y"], "a": [10.0, 5.0], "d": ["none", "heads"]})
    drv = pd.DataFrame({"r": ["A"], "d": ["heads"], "v": [2]})
    res = run(pools, drv).raise_for_error()
    assert res.output(2)["Pool"].tolist() == ["x"] and res.output(0)["Allocated"].sum() == 5.0
    assert run(pools, drv.assign(v=[-1])).status == "aborted"
    assert run_block(HERE, pools, O).status == "aborted"
    assert run(pools, drv, amount_field="zz").status == "aborted"
    r0 = run(pools, drv, decimals=0).raise_for_error().output(0)
    assert r0["Allocated"].iloc[0] == 5.0


def test_sample_and_large():
    res = run_block(HERE, [POOLS, DRV], {"pool_field": "Cost Pool", "amount_field": "Annual Cost (GBP)", "pool_driver_field": "Driver", "receiver_field": "Department",
                                         "driver_field": "Driver", "value_field": "Value"}).raise_for_error()
    a = res.output(0)
    pools = pd.read_csv(POOLS).set_index("Cost Pool")["Annual Cost (GBP)"]
    for p, tot in a.groupby("Pool")["Allocated"].sum().items():
        assert np.isclose(tot, pools[p], atol=1e-9)
    assert res.output(2)["Pool"].tolist() == ["Legal"]
    rng = np.random.default_rng(0)
    bp = pd.DataFrame({"p": [f"P{i}" for i in range(50)], "a": rng.uniform(1000, 1e6, 50).round(2), "d": rng.choice(["a", "b", "c"], 50)})
    bd = pd.DataFrame({"r": np.repeat([f"R{i}" for i in range(5000)], 3), "d": np.tile(["a", "b", "c"], 5000), "v": rng.uniform(0, 100, 15000)})
    t0 = time.time()
    out = run(bp, bd).raise_for_error().output(0)
    assert time.time() - t0 < 120 and np.isclose(out["Allocated"].sum(), bp["a"].sum())
