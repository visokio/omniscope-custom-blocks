import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "loan-book.csv")
F = {"principal_field": "p", "rate_field": "r", "term_field": "t"}


def run(inputs, **opts):
    return run_block(HERE, inputs, {**F, **opts})


def test_annuity_known_payment():
    # 200,000 over 25 years at 5% monthly: payment 1,169.18
    res = run(pd.DataFrame({"p": [200000.0], "r": [5.0], "t": [25]}), term_unit="YEARS").raise_for_error()
    s, m = res.output(0), res.output(1).iloc[0]
    assert len(s) == 300 and abs(s["Payment"].iloc[0] - 1169.18) < 0.01
    assert abs(s["Closing Balance"].iloc[-1]) < 1e-6 and abs(s["Principal Repaid"].sum() - 200000) < 0.05
    assert abs(m["Total Interest"] - (m["Total Paid"] - 200000)) < 0.05


def test_equal_principal_and_interest_only():
    s = run(pd.DataFrame({"p": [1200.0], "r": [0.12], "t": [12]}), repayment_type="STRAIGHT").raise_for_error().output(0)
    assert np.allclose(s["Principal Repaid"], 100) and s["Payment"].is_monotonic_decreasing and abs(s["Interest"].iloc[0] - 12) < 1e-9
    io = run(pd.DataFrame({"p": [1000.0], "r": [12.0], "t": [3]}), repayment_type="INTEREST_ONLY").raise_for_error().output(0)
    assert io["Payment"].tolist() == [10.0, 10.0, 1010.0]


def test_balloon_and_zero_rate_and_quarterly():
    s = run(pd.DataFrame({"p": [20000.0], "r": [0.0], "t": [10], "b": [5000.0]}), balloon_field="b").raise_for_error().output(0)
    assert np.allclose(s["Payment"].iloc[:-1], 1500.0) and abs(s["Payment"].iloc[-1] - 6500.0) < 1e-9
    q = run(pd.DataFrame({"p": [10000.0], "r": [8.0], "t": [24], "d": ["2025-01-31"]}), frequency="QUARTERLY", start_field="d").raise_for_error().output(0)
    assert len(q) == 8 and q["Payment Date"].dt.strftime("%Y-%m-%d").tolist()[:2] == ["2025-04-30", "2025-07-31"]


def test_sample_loan_book_types_and_bad_rows():
    res = run_block(HERE, SAMPLE, {"loan_id_field": "Loan ID", "principal_field": "Principal", "rate_field": "Annual Rate %", "term_field": "Term Months",
                                   "start_field": "Start Date", "balloon_field": "Balloon", "type_field": "Repayment Type"}).raise_for_error()
    s, m = res.output(0), res.output(1).set_index("Loan ID")
    assert m.loc["L-1009", "Status"].startswith("Principal") and m.loc["L-1004", "Repayment Type"] == "Equal principal"
    pcp = s[s["Loan ID"] == "L-1003"]
    assert abs(pcp["Payment"].iloc[-1] - pcp["Payment"].iloc[0] - 11000) < 1.0  # balloon paid with the final payment
    assert (s.groupby("Loan ID")["Closing Balance"].last().abs() < 1e-6).all()


def test_empty_and_bad_options():
    res = run(pd.DataFrame({"p": pd.Series([], dtype="float64"), "r": pd.Series([], dtype="float64"), "t": pd.Series([], dtype="float64")})).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0
    assert run(pd.DataFrame({"p": [1.0], "r": [1.0], "t": [1]}), principal_field="nope").status == "aborted"
    m = run(pd.DataFrame({"p": ["abc", 100.0], "r": [5.0, None], "t": [12, 12]})).raise_for_error().output(1)
    assert m["Status"].str.contains("missing").all()


def test_large_book_is_fast():
    n = 5000
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"p": rng.uniform(5e3, 5e5, n), "r": rng.uniform(2, 12, n), "t": rng.integers(12, 120, n)})
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 90 and len(res.output(1)) == n
