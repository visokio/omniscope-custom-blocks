import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "branch-sales.csv")
ALL = {"annotateData": True, "findIssues": True, "enrichData": True}
ISSUE_FIELDS = ["Row ID", "Issue Type", "Issue Field", "Issue Details"]


def run(data, **options):
    return run_block(HERE, data, {**ALL, **options})


def test_sample_issue_log():
    res = run(SAMPLE).raise_for_error()
    issues = res.output(1)
    assert list(issues.columns) == ISSUE_FIELDS
    assert len(issues) == 11
    by_type = issues.groupby("Issue Type").size().to_dict()
    assert by_type == {"DUPLICATE_ROW": 4, "MISSING_VALUE": 5, "OUTLIER": 2}
    assert sorted(issues.loc[issues["Issue Type"] == "DUPLICATE_ROW", "Row ID"]) == [10, 11, 21, 22]
    missing = issues[issues["Issue Type"] == "MISSING_VALUE"]
    assert dict(zip(missing["Row ID"], missing["Issue Field"])) == {
        6: "Branch", 18: "Branch", 8: "Units", 15: "Unit Price", 24: "Order Date"}
    outliers = issues[issues["Issue Type"] == "OUTLIER"]
    assert dict(zip(outliers["Row ID"], outliers["Issue Field"])) == {14: "Units", 19: "Unit Price"}
    assert "25 records checked; 11 issues found; 4 missing values filled." == res.final_message


def test_sample_annotated_output():
    out = run(SAMPLE).raise_for_error().output(0)
    assert len(out) == 25
    assert list(out.columns) == ["Row ID", "Order", "Branch", "Product", "Units", "Unit Price", "Order Date",
                                 "Issue Flags", "Issue Count"]
    assert out["Row ID"].tolist() == list(range(1, 26))
    assert out["Issue Count"].sum() == 11 and (out["Issue Count"] > 0).sum() == 11
    assert out.loc[out["Row ID"] == 14, "Issue Flags"].item() == "OUTLIER:Units"
    assert out.loc[out["Row ID"] == 1, "Issue Flags"].item() in ("", None) or pd.isna(
        out.loc[out["Row ID"] == 1, "Issue Flags"].item())


def test_sample_enriched_output():
    out = run(SAMPLE).raise_for_error().output(2)
    assert len(out) == 25 and out.columns[-1] == "Was Enriched"
    row = out.set_index("Row ID")
    assert row.loc[6, "Branch"] == "Leeds" and row.loc[18, "Branch"] == "Leeds"  # the most common branch
    assert row.loc[8, "Units"] == 5  # the median, a whole number, so Units stays an integer field
    assert str(out["Units"].dtype) == "Int64"
    assert row.loc[15, "Unit Price"] == 9.625
    assert pd.isna(row.loc[24, "Order Date"])  # dates are not filled
    assert sorted(out.loc[out["Was Enriched"], "Row ID"]) == [6, 8, 15, 18]


def test_each_output_can_be_turned_off():
    res = run_block(HERE, SAMPLE, {"annotateData": False, "findIssues": True, "enrichData": False}).raise_for_error()
    assert set(res.outputs) == {1}
    res = run_block(HERE, SAMPLE, {"annotateData": False, "findIssues": False, "enrichData": True}).raise_for_error()
    assert set(res.outputs) == {2}


def test_defaults_give_annotated_and_issues():
    res = run_block(HERE, SAMPLE).raise_for_error()
    assert set(res.outputs) == {0, 1}


def test_was_enriched_marks_filled_integer_values():
    # The original compared with ne(), which gives <NA> for a filled nullable-integer value, so the record
    # was reported as not enriched
    df = pd.DataFrame({"id": ["a", "b", "c"], "n": [1, None, 3]})  # n arrives as nullable Int64
    out = run(df).raise_for_error().output(2)
    assert out["n"].tolist() == [1, 2, 3]
    assert out["Was Enriched"].tolist() == [False, True, False]


def test_issue_count_with_comma_in_field_name():
    # The original counted commas in Issue Flags, so a field called "Sales, GBP" counted twice
    df = pd.DataFrame({"Sales, GBP": [1.0, None, 3.0], "Region": ["N", "S", "E"]})
    out = run(df).raise_for_error().output(0)
    assert out["Issue Count"].tolist() == [0, 1, 0]


def test_existing_row_id_field_is_kept():
    # The original overwrote an input field called Row ID with its own numbering
    df = pd.DataFrame({"Row ID": ["R-9", "R-7"], "v": [1.0, 2.0]})
    res = run(df).raise_for_error()
    out = res.output(0)
    assert out["Row ID"].tolist() == ["R-9", "R-7"]
    assert out["Row ID 2"].tolist() == [1, 2]
    assert "Row ID 2" in res.output(1).columns
    assert "Row ID -> Row ID 2" in res.final_message


def test_empty_input_gives_empty_outputs_with_fields():
    # The original committed without writing any output
    df = pd.DataFrame({"name": pd.Series([], dtype=object), "n": pd.Series([], dtype="float64")})
    res = run(df).raise_for_error()
    assert set(res.outputs) == {0, 1, 2}
    assert list(res.output(0).columns) == ["Row ID", "name", "n", "Issue Flags", "Issue Count"]
    assert list(res.output(1).columns) == ISSUE_FIELDS
    assert list(res.output(2).columns) == ["Row ID", "name", "n", "Was Enriched"]
    assert all(len(o) == 0 for o in res.outputs.values())


def test_no_input_or_no_output_ticked_aborts():
    # The original reported success with no output in both cases
    res = run_block(HERE, None, ALL)
    assert res.status == "aborted" and "Connect" in res.final_message
    res = run_block(HERE, SAMPLE, {"annotateData": False, "findIssues": False, "enrichData": False})
    assert res.status == "aborted" and "Tick" in res.final_message


def test_field_types_without_spread_or_values():
    df = pd.DataFrame({
        "flag": [True, False, True, True],
        "same": [5.0, 5.0, 5.0, 5.0],           # no spread: no outliers
        "empty": [None, None, None, None],       # all missing: nothing to fill
        "when": pd.to_datetime(["2025-01-01", None, "2025-01-03", "2025-01-04"]),
        "txt": ["x", "y", "y", None],
    })
    res = run(df).raise_for_error()
    issues = res.output(1)
    assert set(issues["Issue Type"]) == {"MISSING_VALUE"}
    assert issues.groupby("Issue Field").size().to_dict() == {"empty": 4, "when": 1, "txt": 1}
    enr = res.output(2)
    assert enr["txt"].tolist() == ["x", "y", "y", "y"] and enr["empty"].isna().all()
    assert enr["flag"].tolist() == [True, False, True, True]


def test_integer_median_with_half_becomes_decimal():
    df = pd.DataFrame({"n": [1, 2, None, 3, 4]})
    out = run(df).raise_for_error().output(2)
    assert out["n"].tolist() == [1.0, 2.0, 2.5, 3.0, 4.0]


def test_mode_tie_takes_first_in_sort_order():
    df = pd.DataFrame({"t": ["pear", "apple", None, "pear", "apple"]})
    assert run(df).raise_for_error().output(2)["t"].tolist()[2] == "apple"


def test_large_input():
    n = 200_000
    rng = np.random.default_rng(1)
    df = pd.DataFrame({
        "id": np.arange(n),
        "x": rng.normal(100, 10, n),
        "cat": rng.choice(["a", "b", "c"], n).astype(object),
    })
    df.loc[rng.choice(n, 1000, replace=False), "cat"] = None
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 60
    issues = res.output(1)
    assert (issues["Issue Type"] == "MISSING_VALUE").sum() == 1000
    assert len(res.output(0)) == n and res.output(2)["cat"].notna().all()


def test_large_input_with_many_issues():
    n = 200_000
    df = pd.DataFrame({f"f{i}": np.where(np.arange(n) % 2 == 0, np.nan, np.arange(n) * 1.0) for i in range(5)})
    df["t"] = None
    t0 = time.time()
    res = run(df).raise_for_error()
    assert time.time() - t0 < 60
    assert len(res.output(1)) == 800_000  # 500,000 + 200,000 missing; the 100,000 empty records are duplicates
