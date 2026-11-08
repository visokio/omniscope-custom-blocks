import os

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
TX = os.path.join(HERE, "sample-data", "transactions.csv")
OB = os.path.join(HERE, "sample-data", "opening-balances.csv")
DF = pd.DataFrame({"a": ["x", "x", "x", "y"], "d": ["2025-01-01", "2025-01-03", "2025-01-03", "2025-01-02"], "v": [-50.0, 30.0, 40.0, 10.0]})
O = {"account_field": "a", "date_field": "d", "amount_field": "v"}


def test_balances_days_and_average():
    res = run_block(HERE, [DF, pd.DataFrame({"a": ["x"], "b": [20.0]})], {**O, "opening_account_field": "a", "opening_balance_field": "b", "as_of": "2025-01-04"}).raise_for_error()
    t = res.output(0)
    assert t["Balance After"].tolist() == [-30.0, 0.0, 40.0, 10.0] and t["Below Zero"].tolist() == ["Yes", "No", "No", "No"]
    s = res.output(1).set_index("a")
    assert s.loc["x", "Lowest Balance"] == -30 and s.loc["x", "Days Below Zero"] == 2 and np.isclose(s.loc["x", "Average Daily Balance"], (-30 - 30 + 40 + 40) / 4)
    assert s.loc["y", "Opening Balance"] == 0 and s.loc["x", "Closing Balance"] == 40


def test_limit_sample_and_bad_inputs():
    t = run_block(HERE, DF, {**O, "limit": 40}).raise_for_error().output(0)
    assert t["Below Limit"].tolist() == ["Yes", "No", "No", "No"]
    res = run_block(HERE, [TX, OB], {"account_field": "Account", "date_field": "Date", "amount_field": "Amount (GBP)", "opening_account_field": "Account",
                                     "opening_balance_field": "Opening Balance (GBP)"}).raise_for_error()
    assert len(res.output(1)) == 25
    assert run_block(HERE, DF, {**O, "amount_field": "zz"}).status == "aborted"
    assert run_block(HERE, DF, {**O, "as_of": "later"}).status == "aborted"
