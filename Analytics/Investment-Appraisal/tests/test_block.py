import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "capital-requests.csv")
O = {"project_field": "p", "time_field": "t", "amount_field": "a"}


def run(df, **opts):
    return run_block(HERE, df, {**O, **opts})


def test_npv_irr_payback_pi():
    df = pd.DataFrame({"p": "x", "t": [0, 1, 2, 3], "a": [-1000.0, 400, 400, 400]})
    r = run(df, discount_rate=0.05).raise_for_error().output(0).iloc[0]
    npv = -1000 + 400 / 1.05 + 400 / 1.05 ** 2 + 400 / 1.05 ** 3
    assert np.isclose(r["NPV"], npv) and np.isclose(r["Profitability Index"], (npv + 1000) / 1000)
    assert abs(-1000 + sum(400 / (1 + r["IRR"]) ** k for k in (1, 2, 3))) < 1e-6
    assert np.isclose(r["Payback"], 2.5) and r["Decision"] == "Accept" and r["Sign Changes"] == 1
    fv = 400 * 1.05 ** 2 + 400 * 1.05 + 400
    assert np.isclose(r["MIRR"], (fv / 1000) ** (1 / 3) - 1)


def test_xirr_matches_published_example():
    # the XIRR example in Microsoft's Excel documentation: result 0.373362535
    df = pd.DataFrame({"p": "x", "t": ["2008-01-01", "2008-03-01", "2008-10-30", "2009-02-15", "2009-04-01"], "a": [-10000.0, 2750, 4250, 3250, 2750]})
    r = run(df, timing="DATE", discount_rate=0.09).raise_for_error()
    assert abs(r.output(0).iloc[0]["IRR"] - 0.373362535) < 1e-6
    f = r.output(1)
    assert "Date" in f.columns and f["Years From Start"].iloc[0] == 0


def test_multiple_irrs_rate_field_and_profile():
    df = pd.DataFrame({"p": "x", "t": [0, 1, 2], "a": [-100.0, 230, -132]})  # IRRs 10% and 20%
    r = run(df, discount_rate=0.12).raise_for_error()
    row = r.output(0).iloc[0]
    assert row["Sign Changes"] == 2 and "2 IRRs" in row["IRR Note"] and np.isclose(row["IRR"], 0.10, atol=1e-6)
    two = pd.concat([df.assign(p="a", rr=0.05), df.assign(p="b", rr=0.15)])
    res = run(two, rate_field="rr").raise_for_error().output(0).set_index("p")
    assert res.loc["a", "Discount Rate"] == 0.05 and res.loc["b", "Discount Rate"] == 0.15
    prof = r.output(2)
    assert len(prof) == 31 and np.isclose(prof[prof["Rate"] == 0]["NPV"].iloc[0], -2.0)


def test_sample_and_aggregation():
    res = run_block(HERE, SAMPLE, {"project_field": "Project", "time_field": "Year", "amount_field": "Cash Flow (GBP k)"}).raise_for_error()
    p = res.output(0).set_index("Project")
    assert p["Rank By NPV"].iloc[0] == 1 and p.loc["Solar panels on depots", "Decision"] == "Reject"
    assert p.loc["Store refit with closure costs", "Sign Changes"] == 2
    dup = pd.DataFrame({"p": "x", "t": [0, 0, 1], "a": [-50.0, -50, 120]})
    assert run(dup).raise_for_error().output(0).iloc[0]["Cash Flows"] == 2


def test_bad_inputs_and_large():
    df = pd.DataFrame({"p": "x", "t": [0, 1], "a": [-1.0, 2]})
    assert run(df, amount_field="zz").status == "aborted"
    assert run(df, discount_rate=-1.5).status == "aborted"
    assert run(df.assign(a=["x", "y"])).raise_for_error().output(0).empty
    rng = np.random.default_rng(0)
    big = pd.DataFrame({"p": np.repeat([f"P{i}" for i in range(300)], 11), "t": np.tile(np.arange(11), 300),
                        "a": np.where(np.tile(np.arange(11), 300) == 0, -1000, rng.normal(150, 30, 3300))})
    t0 = time.time()
    res = run(big).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == 300
