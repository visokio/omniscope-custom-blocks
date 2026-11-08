import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
INV = os.path.join(HERE, "sample-data", "invoices.csv")
FX = os.path.join(HERE, "sample-data", "fx-rates.csv")
L = pd.DataFrame({"id": [1, 2, 3, 4, 5], "k": ["a", "a", "b", "a", "c"], "d": ["2025-01-01", "2025-01-05", "2025-01-03", "2025-01-20", "2025-01-02"]})
R = pd.DataFrame({"k": ["a", "a", "b", "a"], "eff": ["2025-01-02", "2025-01-04", "2025-01-01", "2025-01-10"], "rate": [1.0, 2.0, 3.0, 4.0]})


def run(l, r, **opts):
    return run_block(HERE, [l, r], {"left_date": "d", "right_date": "eff", "left_keys": ["k"], **opts})


def test_backward_forward_nearest():
    o = run(L, R).raise_for_error().output(0)
    assert o["id"].tolist() == [1, 2, 3, 4, 5]  # original order kept
    assert o["rate"].tolist()[1:4] == [2.0, 3.0, 4.0] and pd.isna(o["rate"].iloc[0]) and pd.isna(o["rate"].iloc[4])
    assert o["As Of Status"].tolist() == ["No record in range", "Matched", "Matched", "Matched", "No record in range"]
    assert o["Days From As Of Date"].tolist()[1:4] == [1.0, 2.0, 10.0]
    f = run(L, R, direction="FORWARD").raise_for_error().output(0)
    assert f["rate"].iloc[0] == 1.0 and f["rate"].iloc[1] == 4.0 and pd.isna(f["rate"].iloc[3])
    n = run(L, R, direction="NEAREST").raise_for_error().output(0)
    assert n["rate"].iloc[0] == 1.0 and n["rate"].iloc[3] == 4.0


def test_max_gap_and_end_date():
    o = run(L, R, max_gap_days=5).raise_for_error().output(0)
    assert o["As Of Status"].iloc[3] == "No record in range"
    r2 = R.assign(until=["2025-01-03", "2025-01-09", "2025-12-31", "2025-01-15"])
    o = run(L, r2, right_end_date="until").raise_for_error().output(0)
    assert o["As Of Status"].iloc[3] == "Expired (after end date)" and pd.isna(o["rate"].iloc[3])
    assert "until" not in o.columns  # dates and keys are not brought across by default
    o = run(L, r2, right_end_date="until", fields_to_add=["rate", "until"]).raise_for_error().output(0)
    assert "until" in o.columns and "eff" not in o.columns


def test_no_keys_clashing_names_and_key_types():
    l = pd.DataFrame({"d": ["2025-01-05", "2025-01-07"], "rate": [9, 9]})
    o = run_block(HERE, [l, R], {"left_date": "d", "right_date": "eff"}).raise_for_error().output(0)
    assert o["rate (as of)"].tolist() == [2.0, 2.0] and o["k"].tolist() == ["a", "a"]  # global latest row; clash suffixed
    l2 = pd.DataFrame({"p": [10, 20], "d": ["2025-02-01", "2025-02-01"]})
    r2 = pd.DataFrame({"prod": ["10", "20"], "eff": ["2025-01-01", "2025-01-15"], "price": [5, 7]})
    o = run_block(HERE, [l2, r2], {"left_date": "d", "right_date": "eff", "left_keys": ["p"], "right_keys": ["prod"]}).raise_for_error().output(0)
    assert o["price"].tolist() == [5, 7] and str(o["price"].dtype) == "Int64"  # integer 10 matches text "10"


def test_same_date_duplicates_take_last_and_dayfirst_text():
    r = pd.DataFrame({"k": ["a", "a"], "eff": ["03/01/2025", "03/01/2025"], "rate": [1.0, 1.5]})
    o = run(L.iloc[[1]], r).raise_for_error().output(0)
    assert o["rate"].tolist() == [1.5] and o["As Of Date"].dt.strftime("%Y-%m-%d").tolist() == ["2025-01-03"]


def test_sample_fx():
    res = run_block(HERE, [INV, FX], {"left_date": "Invoice Date", "left_keys": ["Currency"], "right_date": "Rate Date", "max_gap_days": 5}).raise_for_error()
    o = res.output(0)
    bad = o[o["As Of Status"] != "Matched"]
    assert set(bad["Currency"]) <= {"SEK", "CHF"} and (bad["Currency"] == "SEK").sum() == 28
    wk = o[(o["As Of Status"] == "Matched") & (o["Invoice Date"].dt.dayofweek >= 5)]
    assert (wk["Days From As Of Date"] >= 1).all()  # weekend invoices use Friday's rate
    assert o["Invoice"].tolist() == pd.read_csv(INV)["Invoice"].tolist()


def test_bad_inputs_and_empty():
    assert run_block(HERE, L, {"left_date": "d", "right_date": "eff"}).status == "aborted"
    assert run(L, R, left_date="zz").status == "aborted"
    assert run(L, R, right_keys=["k", "eff"]).status == "aborted"
    o = run(L.iloc[0:0], R).raise_for_error().output(0)
    assert len(o) == 0 and "rate" in o.columns
    o = run(L, R.iloc[0:0]).raise_for_error().output(0)
    assert (o["As Of Status"] == "No record in range").all()
    o = run(L.assign(d=["x", None, "2025-01-05", "2025-01-05", "2025-01-05"]), R).raise_for_error().output(0)
    assert o["As Of Status"].tolist()[:2] == ["No date", "No date"]


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 500_000
    l = pd.DataFrame({"k": rng.choice([f"c{i}" for i in range(50)], n),
                      "d": pd.Timestamp("2020-01-01") + pd.to_timedelta(rng.integers(0, 2000, n), unit="D")})
    r = pd.DataFrame({"k": np.repeat([f"c{i}" for i in range(50)], 1500),
                      "eff": np.tile(pd.bdate_range("2019-12-01", periods=1500), 50), "rate": rng.normal(size=75_000)})
    t0 = time.time()
    o = run(l, r).raise_for_error().output(0)
    assert time.time() - t0 < 120 and (o["As Of Status"] == "Matched").mean() > 0.99
