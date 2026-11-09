import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
DATA = os.path.join(HERE, "sample-data", "bank-transactions.csv")
RULES = os.path.join(HERE, "sample-data", "rename-rules.csv")
RENAMED = ["Account Number", "Transaction Date", "Reference", "Debit or Credit", "Amount", "Balance",
           "Merchant Category"]


def rules_file(tmp_path, text, name="rules.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def run(data, rules):
    return run_block(HERE, data, {"rules": rules})


def test_sample_rules_rename_every_field():
    res = run(DATA, RULES).raise_for_error()
    out = res.output(0)
    assert len(out) == 24
    assert list(out.columns) == RENAMED
    original = pd.read_csv(DATA)
    assert out["Reference"].tolist() == original["txn_ref"].tolist()
    assert out["Amount"].sum() == original["amt_gbp"].sum()


def test_block_closes_after_the_stream():
    # The original never called close() after process_stream
    assert run(DATA, RULES).status == "committed"


def test_data_in_several_chunks_keeps_one_schema():
    n = 25_000  # three chunks of 10,000
    df = pd.DataFrame({"acct_no": ["A"] * n, "amt_gbp": np.arange(n, dtype=float), "other": range(n)})
    out = run(df, RULES).raise_for_error().output(0)
    assert list(out.columns) == ["Account Number", "Amount", "other"] and len(out) == n


def test_example_format_with_spaces_after_commas(tmp_path):
    # The original's own example ("Current Name, New Name") gave the heading " New Name" and the block stopped
    rules = rules_file(tmp_path, "Current Name, New Name\nCategory, New Category\nIsin, Isin Number \n")
    df = pd.DataFrame({"Index": [1], "Category": ["Sub"], "Isin": ["XS0076061927"]})
    out = run(df, rules).raise_for_error().output(0)
    assert list(out.columns) == ["Index", "New Category", "Isin Number"]


def test_headings_ignore_capitals_and_a_byte_order_mark(tmp_path):
    p = tmp_path / "bom.csv"
    p.write_bytes("﻿current name,NEW NAME\nCategory,Kind\n".encode("utf-8"))
    out = run(pd.DataFrame({"Category": ["x"]}), str(p)).raise_for_error().output(0)
    assert list(out.columns) == ["Kind"]


def test_field_names_are_matched_exactly_and_unknown_rules_ignored(tmp_path):
    rules = rules_file(tmp_path, "Current Name,New Name\ncategory,Kind\nMissing,Nothing\n")
    out = run(pd.DataFrame({"Category": ["x"]}), rules).raise_for_error().output(0)
    assert list(out.columns) == ["Category"]


def test_rename_onto_an_existing_name_stops_with_a_message(tmp_path):
    # The original wrote two fields with the same name
    rules = rules_file(tmp_path, "Current Name,New Name\nFull,Name\n")
    res = run(pd.DataFrame({"Name": ["a"], "Full": ["b"]}), rules)
    assert res.status == "aborted" and "same name: Name" in res.final_message


def test_swap_two_names(tmp_path):
    rules = rules_file(tmp_path, "Current Name,New Name\nA,B\nB,A\n")
    out = run(pd.DataFrame({"A": [1], "B": ["two"]}), rules).raise_for_error().output(0)
    assert list(out.columns) == ["B", "A"] and out["B"].tolist() == [1]


def test_blank_and_incomplete_rules(tmp_path):
    rules = rules_file(tmp_path, "Current Name,New Name\n,\nA,Alpha\n")
    out = run(pd.DataFrame({"A": [1]}), rules).raise_for_error().output(0)
    assert list(out.columns) == ["Alpha"]
    # The original renamed the field to a missing name (nan)
    rules = rules_file(tmp_path, "Current Name,New Name\nA,\n", "r2.csv")
    res = run(pd.DataFrame({"A": [1]}), rules)
    assert res.status == "aborted" and "no new name: A" in res.final_message
    rules = rules_file(tmp_path, "Current Name,New Name\nA,X\nA,Y\n", "r3.csv")
    res = run(pd.DataFrame({"A": [1]}), rules)
    assert res.status == "aborted" and "more than once: A" in res.final_message


def test_names_that_look_like_numbers_or_placeholders_stay_text(tmp_path):
    rules = rules_file(tmp_path, "Current Name,New Name\n2024,Last year\nNA,Not applicable\n")
    out = run(pd.DataFrame({"2024": [1], "NA": [2]}), rules).raise_for_error().output(0)
    assert list(out.columns) == ["Last year", "Not applicable"]


def test_bad_rules_file(tmp_path):
    rules = rules_file(tmp_path, "From,To\nA,B\n")
    res = run(pd.DataFrame({"A": [1]}), rules)
    assert res.status == "aborted" and "Current Name" in res.final_message and "From, To" in res.final_message
    res = run(pd.DataFrame({"A": [1]}), str(tmp_path / "nowhere.csv"))
    assert res.status == "aborted" and "Could not read" in res.final_message
    res = run(pd.DataFrame({"A": [1]}), None)
    assert res.status == "aborted" and "rename rules CSV file" in res.final_message


def test_empty_input():
    df = pd.DataFrame({"acct_no": pd.Series([], dtype=object), "amt_gbp": pd.Series([], dtype="float64")})
    res = run(df, RULES).raise_for_error()
    out = res.output(0)
    assert len(out) == 0 and list(out.columns) == ["Account Number", "Amount"]


def test_types_are_unchanged():
    df = pd.DataFrame({"acct_no": ["a", None], "txn_dt": pd.to_datetime(["2025-01-01", None]).tz_localize("UTC"),
                       "amt_gbp": [1, None], "flag": [True, False]})
    out = run(df, RULES).raise_for_error().output(0)
    assert str(out["Amount"].dtype) == "Int64" and str(out["Transaction Date"].dtype).endswith("UTC]")
    assert out["flag"].dtype == bool


def test_large_input_and_many_rules(tmp_path):
    n_fields, n = 500, 200_000
    rules = rules_file(tmp_path, "Current Name,New Name\n" + "".join(f"f{i},Field {i}\n" for i in range(n_fields)))
    df = pd.DataFrame(np.ones((n, n_fields), dtype="float64"), columns=[f"f{i}" for i in range(n_fields)])
    t0 = time.time()
    out = run(df, rules).raise_for_error().output(0)
    assert time.time() - t0 < 60
    assert len(out) == n and out.columns[-1] == "Field 499"


# ---- Rules written in the block (the Rename rules text option) ----

SAMPLE_TEXT = ("acct_no = Account Number; txn_dt = Transaction Date; txn_ref = Reference; dr_cr = Debit or Credit; "
               "amt_gbp = Amount; bal_gbp = Balance; mcc = Merchant Category; branch_cd = Branch Code")


def test_rules_text_gives_the_same_result_as_the_file():
    from_file = run(DATA, RULES).raise_for_error().output(0)
    from_text = run_block(HERE, DATA, {"rulesText": SAMPLE_TEXT}).raise_for_error().output(0)
    pd.testing.assert_frame_equal(from_text, from_file)
    assert list(from_text.columns) == RENAMED and len(from_text) == 24


def test_rules_text_one_per_line_and_precedence_over_the_file():
    text = "acct_no = Account\r\n\n  amt_gbp=Value  \n"
    out = run_block(HERE, DATA, {"rulesText": text, "rules": RULES}).raise_for_error().output(0)
    assert list(out.columns)[:2] == ["Account", "txn_dt"] and "Value" in out.columns
    # an empty text option falls back to the file
    out = run_block(HERE, DATA, {"rulesText": "  ", "rules": RULES}).raise_for_error().output(0)
    assert list(out.columns) == RENAMED


def test_rules_text_mistakes_stop_with_a_message():
    res = run_block(HERE, DATA, {"rulesText": "acct_no Account"})
    assert res.status == "aborted" and "no '='" in res.final_message
    res = run_block(HERE, DATA, {"rulesText": "acct_no = "})
    assert res.status == "aborted" and "no new name: acct_no" in res.final_message
    res = run_block(HERE, DATA, {"rulesText": "acct_no = A; txn_dt = A"})
    assert res.status == "aborted" and "same name: A" in res.final_message
    res = run_block(HERE, DATA, {})
    assert res.status == "aborted" and "Rename rules option" in res.final_message
