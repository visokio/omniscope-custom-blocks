import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "supplier-master.csv")
DF = pd.DataFrame({"id": [1, 2, 3, 4, 5], "email": ["A@x.com", "a@x.com ", None, None, "b@y.com"], "name": ["Ann Lee", "Ann Lee", "ann lee", "Bob", "Bob"],
                   "pc": ["LS1 4AP", None, "ls14ap", "M1", "M1"], "tel": ["0113 1", "", "(0113) 1", None, None], "d": ["2024-01-01", "2025-01-01", "2023-01-01", "2025-05-01", "2025-06-01"]})


def run(df, **opts):
    return run_block(HERE, df, opts)


def test_groups_chain_and_survivor_rules():
    r = run(DF, match_keys="email; name + pc").raise_for_error()
    rec = r.output(0)
    assert rec["Duplicate Group"].tolist()[:3] == [1, 1, 1]  # 1-2 by email, 1-3 by name + postcode
    assert rec["Group Size"].tolist() == [3, 3, 3, 2, 2] and rec["Survivor"].tolist()[:3] == ["Yes", "No", "No"]  # most complete
    late = run(DF, match_keys="email; name + pc", survivor_rule="LATEST", rule_field="d").raise_for_error().output(0)
    assert late["Survivor"].tolist() == ["No", "Yes", "No", "No", "Yes"]
    early = run(DF, match_keys="email; name + pc", survivor_rule="EARLIEST", rule_field="d").raise_for_error().output(0)
    assert early["Survivor"].tolist()[:3] == ["No", "No", "Yes"]


def test_fill_gaps_and_digits_only():
    s = run(DF, match_keys="email; name + pc", survivor_rule="LATEST", rule_field="d").raise_for_error().output(1)
    row = s[s["id"] == 2].iloc[0]
    assert row["pc"] == "LS1 4AP" and "pc" in row["Fields Filled From Duplicates"] and row["Records Merged"] == 3
    nf = run(DF, match_keys="email", fill_gaps=False).raise_for_error().output(1)
    assert nf["Fields Filled From Duplicates"].isna().all()
    t = run(DF, match_keys="tel", digits_only_fields=["tel"]).raise_for_error().output(0)
    assert t["Group Size"].iloc[0] == 2 and t["Group Size"].iloc[2] == 2


def test_sample_and_bad_inputs():
    res = run_block(HERE, SAMPLE, {"match_keys": "Email; Name + Postcode; Phone; VAT Number", "digits_only_fields": ["Phone"], "survivor_rule": "LATEST",
                                   "rule_field": "Last Updated"}).raise_for_error()
    assert len(res.output(1)) == 7 and len(res.output(2)) == 4
    assert run(DF, match_keys="").status == "aborted"
    assert run(DF, match_keys="zz").status == "aborted"
    assert run(DF, match_keys="email", survivor_rule="LATEST").status == "aborted"
    assert len(run(DF.iloc[0:0], match_keys="email").raise_for_error().output(1)) == 0


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 100_000
    big = pd.DataFrame({"e": [f"u{i}@x.com" for i in rng.integers(0, 70_000, n)], "n": rng.choice(["a", "b", "c"], n), "p": rng.integers(0, 50_000, n).astype(str)})
    t0 = time.time()
    res = run(big, match_keys="e; n + p", fill_gaps=False).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(1)) < n
