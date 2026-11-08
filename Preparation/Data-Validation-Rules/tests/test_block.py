import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
DATA = os.path.join(HERE, "sample-data", "customer-master.csv")
RULES = os.path.join(HERE, "sample-data", "rules.csv")
DF = pd.DataFrame({"id": ["a", "b", "b", "c", None], "email": ["x@y.com", "bad", None, "z@q.co.uk", "a@b.org"],
                   "amt": [10, 200, 50, -1, 30], "limit": [100, 100, 100, 100, 20], "pc": ["LS1 4AP", "LS14AP", "XYZ", None, "sw1a 1aa"],
                   "country": ["UK", "UK", "UK", "UK", "FR"], "d": ["2024-01-01", "2099-01-01", "31/12/2023", "nope", None], "st": ["A", "a", "B", "", "C"]})


def run(df, rules, **opts):
    return run_block(HERE, df, {"rules": rules, **opts})


def failing(res, rule_check):
    s = res.output(1).set_index("Check")
    return int(s.loc[rule_check, "Rows Failing"])


def test_each_check():
    rules = "\n".join(["id | NOT_EMPTY", "id | UNIQUE", "email | EMAIL", "amt | MIN | 0", "amt | MAX | 100 | Warning", "pc | UK_POSTCODE",
                       "pc | REQUIRED_IF | country = UK", "d | IS_DATE", "d | NOT_FUTURE | 2030-01-01", "st | ALLOWED | A|B", "amt | COMPARE | <= limit",
                       "id | PATTERN | [a-z]", "id | MAX_LENGTH | 1", "amt | BETWEEN | 0..150"])
    res = run(DF, rules, key_fields=["id"]).raise_for_error()
    s = res.output(1).set_index("Rule")
    f = dict(zip(s.index, s["Rows Failing"]))
    assert f["id not empty"] == 1 and f["id unique"] == 2 and f["email email"] == 1
    assert f["amt min 0"] == 1 and f["amt max 100"] == 1 and f["pc uk postcode"] == 1 and f["pc required if country = UK"] == 1
    assert f["d is date"] == 1 and f["d not future 2030-01-01"] == 2  # 2099 and the unreadable value
    assert f["st allowed A|B"] == 1 and f["amt compare <= limit"] == 2 and f["amt between 0..150"] == 2
    assert s.loc["amt max 100", "Status"] == "Warning" and s.loc["id not empty", "Status"] == "Fail" and s.loc["id pattern [a-z]", "Status"] == "Pass"
    rows = res.output(2)
    assert rows["Valid"].tolist() == ["Yes", "No", "No", "No", "No"]
    v = res.output(0)
    assert set(v.columns) >= {"Row Number", "id", "Rule", "Value Found"} and (v["Row Number"] >= 1).all()


def test_rules_table_and_typed_rules_together():
    rt = pd.DataFrame({"F": ["amt"], "C": ["min"], "V": ["0"], "S": ["warn"], "N": ["Positive amount"]})
    res = run_block(HERE, [DF, rt], {"rules": "email | EMAIL", "rule_field_field": "F", "rule_check_field": "C", "rule_value_field": "V",
                                     "rule_severity_field": "S", "rule_name_field": "N"}).raise_for_error()
    s = res.output(1).set_index("Rule")
    assert s.loc["Positive amount", "Severity"] == "Warning" and "email email" in s.index


def test_sample_master_data():
    res = run_block(HERE, [DATA, RULES], {"key_fields": ["Customer ID"], "rule_field_field": "Field", "rule_check_field": "Check", "rule_value_field": "Value",
                                          "rule_severity_field": "Severity", "rule_name_field": "Rule Name"}).raise_for_error()
    s = res.output(1).set_index("Rule")
    assert s.loc["Valid email", "Rows Failing"] == 6 and s.loc["Customer ID unique", "Rows Failing"] == 6
    assert s.loc["Credit limit in range", "Rows Failing"] == 3 and s.loc["VAT number format", "Status"] == "Pass"
    assert len(res.output(2)) == 800


def test_bad_rules_and_empty():
    assert run(DF, "").status == "aborted"
    assert run(DF, "zz | NOT_EMPTY").status == "aborted"
    assert run(DF, "id | SOMETHING").status == "aborted"
    assert run(DF, "amt | COMPARE | <= nope").status == "aborted"
    assert run(DF, "id | PATTERN | [").status == "aborted"
    assert run(DF, "amt | BETWEEN | 5").status == "aborted"
    assert run(DF, "just one part").status == "aborted"
    res = run(DF.iloc[0:0], "id | NOT_EMPTY").raise_for_error()
    assert len(res.output(0)) == 0 and res.output(1)["Rows Failing"].iloc[0] == 0


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 200_000
    df = pd.DataFrame({"id": np.arange(n).astype(str), "v": rng.normal(100, 30, n), "e": [f"u{i}@x.com" for i in range(n)],
                       "s": rng.choice(["A", "B", "C", "Z"], n), "d": (pd.Timestamp("2020-01-01") + pd.to_timedelta(rng.integers(0, 2000, n), unit="D")).strftime("%Y-%m-%d")})
    rules = "id | UNIQUE\nv | BETWEEN | 0..200\ne | EMAIL\ns | ALLOWED | A|B|C\nd | IS_DATE\nd | NOT_FUTURE"
    t0 = time.time()
    res = run(df, rules).raise_for_error()
    assert time.time() - t0 < 120 and res.output(1).set_index("Check").loc["ALLOWED", "Rows Failing"] == (df["s"] == "Z").sum()
