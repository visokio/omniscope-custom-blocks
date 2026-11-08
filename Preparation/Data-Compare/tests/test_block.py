import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
BEFORE = os.path.join(HERE, "sample-data", "customers-before.csv")
AFTER = os.path.join(HERE, "sample-data", "customers-after.csv")
OLD = pd.DataFrame({"id": [1, 2, 3, 4], "name": ["Ann", "Bob", "Cat", "Dan"], "amt": [10.0, 20.0, 30.0, np.nan], "when": ["2025-01-01"] * 4})
NEW = pd.DataFrame({"id": [1, 2, 3, 5], "name": ["Ann", "bob ", "Kat", "Eve"], "amt": [10.0, 20.004, 35.0, 1.0], "when": ["2025-01-01", "2025-01-02", "2025-01-01", "2025-01-01"]})


def run(o, n, **opts):
    return run_block(HERE, [o, n], opts)


def test_statuses_and_differences():
    res = run(OLD, NEW, key_fields=["id"]).raise_for_error()
    r = res.output(0).set_index("id")
    assert r.loc[4, "Status"] == "Removed" and r.loc[5, "Status"] == "Added"
    assert r.loc[2, "Status"] == "Changed" and r.loc[2, "Changed Fields"] == "name; amt; when"
    assert r.loc[1, "Status"] == "Unchanged" and r.loc[3, "Fields Changed"] == 2
    d = res.output(1)
    row = d[(d["id"] == 3) & (d["Field"] == "amt")].iloc[0]
    assert row["Old Value"] == "30" and row["New Value"] == "35" and row["Change"] == 5
    w = d[(d["id"] == 2) & (d["Field"] == "when")].iloc[0]
    assert w["Change"] == 1.0  # days
    f = res.output(2).set_index("Field")
    assert f.loc["amt", "Values Changed"] == 2 and f.loc["id", "Status"] == "Key"


def test_tolerance_case_and_trim():
    res = run(OLD, NEW, key_fields=["id"], tolerance=0.01, ignore_case=True, trim=True).raise_for_error()
    r = res.output(0).set_index("id")
    assert r.loc[2, "Changed Fields"] == "when"
    d = res.output(1)
    assert d[d["Field"] == "name"]["Old Value"].tolist() == ["Cat"]  # originals are shown, not normalised text
    res = run(OLD, NEW, key_fields=["id"], relative_tolerance=0.2).raise_for_error()
    assert "amt" not in (res.output(0).set_index("id").loc[3, "Changed Fields"] or "")


def test_whole_row_matching_and_duplicates():
    o = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    n = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    r = run(o, n).raise_for_error().output(0)
    assert sorted(r["Status"]) == ["Added", "Removed", "Unchanged", "Unchanged"]
    o2 = pd.DataFrame({"id": [1, 1, 2], "v": [1, 2, 3]})
    n2 = pd.DataFrame({"id": [1, 2], "v": [1, 4]})
    res = run(o2, n2, key_fields=["id"]).raise_for_error()
    r = res.output(0)
    assert (r["Status"] == "Duplicate key (old)").sum() == 2 and (r["Status"] == "Duplicate key (new)").sum() == 1
    assert r[r["Status"] == "Changed"]["id"].tolist() == [2]
    assert "duplicate keys" in res.final_message


def test_schema_differences_and_types():
    o = pd.DataFrame({"id": ["1", "2"], "old_only": [1, 2], "v": [1, 2]})
    n = pd.DataFrame({"id": [1, 2], "new_only": ["a", "b"], "v": [1.0, 2.0]})
    res = run(o, n, key_fields=["id"]).raise_for_error()
    f = res.output(2).set_index("Field")
    assert f.loc["old_only", "Status"] == "Only in old" and f.loc["new_only", "Status"] == "Only in new"
    assert (res.output(0)["Status"] == "Unchanged").all()  # text "1" key matches integer 1; 1 == 1.0
    # Omniscope type names, not pandas dtypes, so host and Docker mode report the same thing
    assert f.loc["v", ["Old Type", "New Type"]].tolist() == ["Integer number", "Decimal number"]
    assert f.loc["new_only", "New Type"] == "Text"
    dt = run(OLD, NEW, key_fields=["id"]).raise_for_error().output(2).set_index("Field")
    assert dt.loc["when", ["Old Type", "New Type"]].tolist() == ["Date", "Date"]  # date text arrives as dates


def test_sample_extracts():
    res = run_block(HERE, [BEFORE, AFTER], {"key_fields": ["Customer ID"], "tolerance": 0.01, "ignore_case": True}).raise_for_error()
    c = res.output(0)["Status"].value_counts()
    assert c["Added"] == 22 and c["Removed"] == 14 and c["Duplicate key (new)"] == 2
    f = res.output(2).set_index("Field")
    assert f.loc["Name", "Values Changed"] == 0 and f.loc["Credit Limit", "Values Changed"] == 12


def test_bad_inputs_and_empty():
    assert run(OLD, NEW, key_fields=["nope"]).status == "aborted"
    assert run(OLD, NEW, key_fields=["id"], compare_fields=["zzz"]).status == "aborted"
    assert run_block(HERE, OLD, {"key_fields": ["id"]}).status == "aborted"  # second input missing
    res = run(OLD.iloc[0:0], NEW.iloc[0:0], key_fields=["id"]).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0
    res = run(OLD.iloc[0:0], NEW, key_fields=["id"]).raise_for_error()
    assert (res.output(0)["Status"] == "Added").all()


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 200_000
    o = pd.DataFrame({"id": np.arange(n), "a": rng.normal(size=n), "b": rng.choice(list("abcdef"), n), "c": rng.integers(0, 100, n)})
    nw = o.sample(frac=0.98, random_state=1).copy()
    ch = nw.sample(frac=0.05, random_state=2).index
    nw.loc[ch, "a"] += 1
    t0 = time.time()
    res = run(o, nw, key_fields=["id"]).raise_for_error()
    assert time.time() - t0 < 120
    c = res.output(0)["Status"].value_counts()
    assert c["Removed"] == n - len(nw) and c["Changed"] == len(ch)
