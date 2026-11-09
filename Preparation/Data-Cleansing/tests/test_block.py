import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = {"path": os.path.join(HERE, "sample-data", "customer-contacts.csv"), "raw": True}  # placeholders kept as text
DEMO = {"null_tokens": "NULL, N/A, -", "collapse_whitespace": True, "remove_invisible": True,
        "modify_case": "TITLE", "case_fields": ["Name", "City", "Segment"], "convert_numbers": True,
        "remove_null_columns": True}


def run(inputs, **opts):
    return run_block(HERE, inputs, opts)


def test_demo_settings_clean_the_sample():
    res = run(SAMPLE, **DEMO).raise_for_error()
    out = res.output(0).set_index("Customer ID")
    assert len(out) == 12  # two all-empty rows removed
    assert "Legacy Code" not in out.columns  # empty field removed
    assert out.loc["C-1001", "Name"] == "Jane Smith"
    assert out.loc["C-1002", "Name"] == "Mohammed Ali"  # repeated spaces collapsed
    assert out.loc["C-1003", "Name"] == "O'Brien, Siobhan"
    assert out.loc["C-1010", "Name"] == "Fiona MacLeod"  # deliberate mixed case kept
    assert out.loc["C-1004", "Name"] == "Li Wei"  # non-breaking space normalised
    assert out.loc["C-1004", "Email"] == "li.wei@example.com"  # zero-width space removed
    assert out.loc["C-1001", "Email"] == "Jane.Smith@Example.com"  # case only in chosen fields
    assert out.loc["C-1003", "Email"] == ""  # placeholder N/A -> missing -> blank
    assert out.loc["C-1005", "Phone"] == ""
    assert out.loc["C-1004", "Phone"] == "07700 900004"  # leading zero: stays text
    assert out["Orders"].dtype == "Int64" and out.loc["C-1008", "Orders"] == 0
    assert out.loc["C-1001", "City"] == "Leeds" and out.loc["C-1002", "City"] == "Leeds"
    rep = res.output(1).set_index("Field")
    assert rep.loc["Orders", "Converted To Number"] == "Yes"
    assert rep.loc["Legacy Code", "Field Removed"] == "Yes"
    assert rep.loc["(empty rows removed)", "Values Changed"] == 2


def test_defaults_apply_the_standard_checklist():
    df = pd.DataFrame({"a": ["  x ", None, "y"], "n": [1.5, np.nan, 2.0]})
    out = run(df).raise_for_error().output(0)
    assert len(out) == 2  # row 2 is empty in every field, so it is removed by default
    out = run(df, remove_null_rows=False).raise_for_error().output(0)
    assert out["a"].tolist() == ["x", "", "y"]
    assert out["n"].tolist() == [1.5, 0.0, 2.0]


def test_character_removal_options():
    df = pd.DataFrame({"code": ["AB-12 cd!", "x 9.9"]})
    out = run(df, remove_letters=True, remove_punctuation=True, remove_all_whitespace=True).raise_for_error().output(0)
    assert out["code"].tolist() == ["12", "99"]
    out = run(df, remove_numbers=True, modify_case="UPPER").raise_for_error().output(0)
    assert out["code"].tolist() == ["AB- CD!", "X ."]


def test_only_selected_fields_are_cleansed():
    df = pd.DataFrame({"a": [" x "], "b": [" y "]})
    out = run(df, fields=["a"]).raise_for_error().output(0)
    assert out["a"][0] == "x" and out["b"][0] == " y "


def test_currency_and_thousands_convert():
    df = pd.DataFrame({"amount": ["£1,250.50", " 300 ", "N/A", "-12"]})
    out = run(df, null_tokens="N/A", convert_numbers=True, remove_null_rows=False).raise_for_error().output(0)
    assert out["amount"].dtype == "float64"
    assert out["amount"].tolist() == [1250.5, 300.0, 0.0, -12.0]


def test_empty_input():
    df = pd.DataFrame({"a": pd.Series([], dtype=object), "b": pd.Series([], dtype="float64")})
    res = run(df, **{**DEMO, "case_fields": []}).raise_for_error()
    assert len(res.output(0)) == 0
    assert set(res.output(1)["Field"]) >= {"a", "b"}


def test_wrong_types_dates_and_bools_are_left_alone():
    df = pd.DataFrame({"when": pd.to_datetime(["2024-01-01", None]), "flag": [True, False], "n": pd.array([1, None], dtype="Int64")})
    out = run(df).raise_for_error().output(0)
    assert pd.api.types.is_datetime64_any_dtype(out["when"])
    assert out["flag"].tolist() == [True, False]
    assert out["n"].tolist() == [1, 0]


def test_unknown_field_aborts():
    res = run(SAMPLE, fields=["Nope"])
    assert res.status == "aborted" and "Nope" in res.final_message


def test_large_input_is_fast():
    n = 200_000
    df = pd.DataFrame({"name": ["  jane   SMITH "] * n, "amt": ["£1,000"] * (n - 1) + ["N/A"], "x": np.arange(n, dtype=float)})
    t0 = time.time()
    out = run(df, null_tokens="N/A", collapse_whitespace=True, modify_case="TITLE", convert_numbers=True).raise_for_error().output(0)
    assert time.time() - t0 < 60
    assert out["name"].iloc[0] == "Jane Smith" and out["amt"].iloc[0] == 1000
