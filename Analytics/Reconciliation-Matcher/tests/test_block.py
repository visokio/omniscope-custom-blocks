import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
BANK = os.path.join(HERE, "sample-data", "bank-statement.csv")
BOOK = os.path.join(HERE, "sample-data", "cash-book.csv")
O = {"amount_field_a": "amt", "amount_field_b": "amt", "date_field_a": "d", "date_field_b": "d", "reference_field_a": "ref", "reference_field_b": "ref"}


def run(a, b, **opts):
    return run_block(HERE, [a, b], {**O, **opts})


def test_exact_amount_and_unmatched():
    a = pd.DataFrame({"amt": [100.0, 50.0, 75.0, 9.99], "d": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"], "ref": ["INV 1", "X", "Y", "FEE"]})
    b = pd.DataFrame({"amt": [100.0, 50.0, 75.01, 300.0], "d": ["2025-01-01", "2025-01-04", "2025-01-03", "2025-01-02"], "ref": ["inv-1", "Z", "Y", "Q"]})
    res = run(a, b, tolerance=0.01, date_window=3).raise_for_error()
    m = res.output(2).set_index("Rule")
    assert m.loc["Exact", "Amount 1"] == 100.0
    s1, s2 = res.output(0), res.output(1)
    assert s1["Match Status"].tolist() == ["Matched", "Matched", "Matched", "Unmatched"]
    assert s2["Match Status"].tolist() == ["Matched", "Matched", "Matched", "Unmatched"]
    assert set(s1["Match Rule"].dropna()) == {"Exact", "Amount and date"}
    assert np.isclose(res.output(2)["Difference"].abs().max(), 0.01)


def test_date_window_and_closest_date_wins():
    a = pd.DataFrame({"amt": [-365.0, -365.0], "d": ["2025-01-03", "2025-01-10"], "ref": ["DD", "DD"]})
    b = pd.DataFrame({"amt": [-365.0, -365.0, -365.0], "d": ["2025-01-09", "2025-01-02", "2025-01-30"], "ref": ["", "", ""]})
    res = run(a, b, date_window=3).raise_for_error()
    s2 = res.output(1)
    assert s2["Match Status"].tolist() == ["Matched", "Matched", "Unmatched"]
    m = res.output(2)
    assert (m["Date Difference (days)"].abs() == 1).all()
    assert (run(a, b, date_window=0).raise_for_error().output(1)["Match Status"] == "Unmatched").all()


def test_sign_flip_and_must_agree():
    a = pd.DataFrame({"amt": [100.0, 100.0], "cur": ["GBP", "EUR"]})
    b = pd.DataFrame({"amt": [-100.0, -100.0], "cur": ["EUR", "USD"]})
    o = {"amount_field_a": "amt", "amount_field_b": "amt"}
    res = run_block(HERE, [a, b], {**o, "sign": "OPPOSITE", "match_fields": ["cur"]}).raise_for_error()
    assert res.output(0)["Match Status"].tolist() == ["Unmatched", "Matched"]
    assert res.output(2)["Amount 2"].tolist() == [-100.0] and res.output(2)["Difference"].tolist() == [0.0]
    assert (run_block(HERE, [a, b], o).raise_for_error().output(0)["Match Status"] == "Unmatched").all()


def test_group_matches_both_ways():
    a = pd.DataFrame({"amt": [2500.0, 1000.0, 800.0], "d": ["2025-01-05"] * 3, "ref": ["REMIT 9", "DEP 1", "DEP 1"]})
    b = pd.DataFrame({"amt": [1250.0, 830.4, 419.6, 1800.0], "d": ["2025-01-04"] * 4, "ref": ["remit-9", "REMIT9", "Remit 9", "DEP-1"]})
    res = run(a, b).raise_for_error()
    m = res.output(2).set_index("Rule")
    assert m.loc["Group (one to many)", "Items In 2"] == 3 and m.loc["Group (many to one)", "Items In 1"] == 2
    assert (res.output(0)["Match Status"] == "Matched").all() and (res.output(1)["Match Status"] == "Matched").all()
    assert (run(a, b, group_matching=False).raise_for_error().output(0)["Match Status"] == "Unmatched").all()


def test_sample_reconciliation():
    res = run_block(HERE, [BANK, BOOK], {"amount_field_a": "Amount", "date_field_a": "Value Date", "reference_field_a": "Narrative",
                                         "amount_field_b": "Amount (GBP)", "date_field_b": "Posting Date", "reference_field_b": "Reference",
                                         "tolerance": 0.01}).raise_for_error()
    u1 = res.output(0)[res.output(0)["Match Status"] == "Unmatched"]
    u2 = res.output(1)[res.output(1)["Match Status"] == "Unmatched"]
    assert sorted(u1["Narrative"]) == ["ACCOUNT FEE", "CARD CHARGES", "INTEREST", "RETURNED ITEM"]
    assert len(u2) == 14
    s = res.output(3).set_index(["Side", "Status"])
    assert s.loc[("Matches", "Group (one to many)"), "Items"] == 1


def test_bad_inputs_and_empty():
    a = pd.DataFrame({"amt": [1.0], "d": ["2025-01-01"], "ref": ["a"]})
    assert run_block(HERE, a, O).status == "aborted"
    assert run(a, a, amount_field_a="nope").status == "aborted"
    assert run(a, a, date_field_b="").status == "aborted"  # date on one side only
    assert run(a, a, match_fields=["zz"]).status == "aborted"
    res = run(a.iloc[0:0], a).raise_for_error()
    assert len(res.output(2)) == 0 and res.output(1)["Match Status"].tolist() == ["Unmatched"]
    res = run(a.assign(amt=["x"]), a).raise_for_error()
    assert res.output(0)["Match Status"].tolist() == ["Unmatched"] and "without a valid amount" in res.final_message


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 40_000
    amt = np.round(rng.gamma(2, 300, n), 2)
    day = rng.integers(0, 365, n)
    a = pd.DataFrame({"amt": amt, "d": (pd.Timestamp("2025-01-01") + pd.to_timedelta(day, unit="D")).strftime("%Y-%m-%d"),
                      "ref": [f"R{i}" for i in range(n)]})
    b = a.sample(frac=0.97, random_state=1).copy()
    b["d"] = (pd.to_datetime(b["d"]) + pd.to_timedelta(rng.integers(0, 3, len(b)), unit="D")).dt.strftime("%Y-%m-%d")
    b["ref"] = ""
    t0 = time.time()
    res = run(a, b, tolerance=0.01, date_window=3).raise_for_error()
    assert time.time() - t0 < 120
    assert (res.output(1)["Match Status"] == "Matched").mean() > 0.99
