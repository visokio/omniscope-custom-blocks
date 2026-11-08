import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
DATA = os.path.join(HERE, "sample-data")
RULES = os.path.join(DATA, "schema-rules.csv")
NORTH = {"path": os.path.join(DATA, "orders-north.csv")}
SOUTH = {"path": os.path.join(DATA, "orders-south.csv")}
CANONICAL = ["order_id", "order_date", "customer", "sku", "quantity", "unit_price", "paid", "currency"]


def rules_file(tmp_path, text):
    p = tmp_path / "rules.csv"
    p.write_text(text)
    return str(p)


def run(inp, rules=RULES, **opts):
    return run_block(HERE, inp, {"rules": rules, **opts})


def test_sample_north_maps_combines_and_converts():
    res = run(NORTH).raise_for_error()
    out = res.output(0)
    assert len(out) == 10
    assert list(out.columns) == CANONICAL[:-1] + ["Notes"]
    by_id = out.set_index("order_id")
    # dd/mm/yyyy text read with the rule's format
    assert by_id.loc["N-1001", "order_date"] == pd.Timestamp("2025-02-03", tz="UTC")
    assert pd.api.types.is_datetime64_any_dtype(out["order_date"])
    # Qty and Quantity combined: each record takes whichever is filled in
    assert by_id["quantity"].tolist()[:6] == [12, 4, 15, 20, 6, 30]
    assert str(out["quantity"].dtype) == "Int64"
    # "two" can't be read as a number: empty, and counted in the message
    assert pd.isna(by_id.loc["N-1009", "quantity"])
    assert any("quantity 1" in m for m in res.messages)
    # Paid: Yes/No read as booleans, empty gets the default false
    assert by_id["paid"].tolist() == [True, True, False, True, False, False, True, True, False, True]
    assert out["unit_price"].dtype == "float64" and by_id.loc["N-1002", "unit_price"] == 18.0
    # an unmapped field passes through, and the message says what happened
    assert by_id.loc["N-1002", "Notes"] == "Delivered to side gate"
    assert "Mapped 7 canonical field(s)" in res.messages[0] and "Notes" in res.messages[0]


def test_two_exports_give_the_same_schema_with_every_canonical_field():
    north = run(NORTH, add_missing_canonical=True, passthrough_unmapped=False).raise_for_error().output(0)
    south = run(SOUTH, add_missing_canonical=True, passthrough_unmapped=False).raise_for_error().output(0)
    assert list(north.columns) == list(south.columns) == CANONICAL
    assert north.dtypes.astype(str).tolist() == south.dtypes.astype(str).tolist()
    assert set(north["currency"]) == {"GBP"}  # no input field: filled with the default
    s = south.set_index("order_id")
    assert s.loc["S-2003", "order_date"] == pd.Timestamp("2025-02-04", tz="UTC")  # ISO text
    assert s.loc["S-2005", "customer"] == "Linton Landscapes" and s.loc["S-2005", "quantity"] == 12
    assert s["paid"].tolist() == [True, False, True, False, True, True]
    both = pd.concat([north, south], ignore_index=True)
    assert len(both) == 16 and both["quantity"].sum() == 12 + 4 + 15 + 20 + 6 + 30 + 8 + 40 + 102


def test_without_output_every_field_the_canonical_fields_take_the_input_order():
    df = pd.DataFrame({"Extra": ["e"], "Units": [3], "Order No": ["A-1"]})
    out = run(df).raise_for_error().output(0)
    assert list(out.columns) == ["Extra", "quantity", "order_id"]  # currency etc. not added
    out = run(df, add_missing_canonical=True).raise_for_error().output(0)
    assert list(out.columns) == CANONICAL + ["Extra"]


def test_canonical_name_first_then_aliases_in_order(tmp_path):
    rules = rules_file(tmp_path, "canonical,aliases\nquantity,Units|Qty\n")
    df = pd.DataFrame({"Qty": ["q1", "q2", "q3"], "Units": ["u1", "u2", None], "QUANTITY": ["c1", None, None]})
    # QUANTITY matches the canonical name loosely, so it comes first; then Units, then Qty, as the rule lists them
    out = run(df, rules).raise_for_error().output(0)
    assert out["quantity"].tolist() == ["c1", "u2", "q3"]


def test_empty_default_leaves_text_missing(tmp_path):
    # The original block filled missing text with "nan" when the rule's default cell was empty
    rules = rules_file(tmp_path, "canonical,aliases,type,default\ncustomer,Client,string,\n")
    out = run(pd.DataFrame({"Client": ["Ann", None]}), rules).raise_for_error().output(0)
    assert out["customer"].iloc[0] == "Ann" and pd.isna(out["customer"].iloc[1])


def test_no_default_means_missing_stays_missing(tmp_path):
    # The original block put 0, 1970-01-01 and False in place of missing values when no default was given
    rules = rules_file(tmp_path, "canonical,aliases,type,default\nqty,Qty,number,\nok,OK,boolean,\nwhen,When,date,\n")
    df = pd.DataFrame({"Qty": [1.5, None], "OK": ["yes", None], "When": ["2025-01-02", None]})
    out = run(df, rules).raise_for_error().output(0)
    assert out["qty"].iloc[0] == 1.5 and pd.isna(out["qty"].iloc[1])
    assert out["ok"].iloc[0] and pd.isna(out["ok"].iloc[1])
    assert pd.isna(out["when"].iloc[1])


def test_defaults_are_typed(tmp_path):
    rules = rules_file(tmp_path, "canonical,aliases,type,default\nqty,Qty,integer,0\n"
                                 "when,When,date,2025-01-01\nok,OK,boolean,true\nregion,Region,string,Unknown\n")
    df = pd.DataFrame({"Qty": [None, 7], "When": [None, "2025-03-04"], "OK": [None, "no"], "Region": [None, "N"]})
    out = run(df, rules).raise_for_error().output(0)
    assert out["qty"].tolist() == [0, 7]
    assert out["when"].tolist() == [pd.Timestamp("2025-01-01", tz="UTC"), pd.Timestamp("2025-03-04", tz="UTC")]
    assert out["ok"].tolist() == [True, False] and out["region"].tolist() == ["Unknown", "N"]


def test_match_names_loosely_can_be_turned_off(tmp_path):
    # The original block read the option under the wrong name, so names were always matched loosely
    rules = rules_file(tmp_path, "canonical,aliases\norder_id,OrderID\n")
    df = pd.DataFrame({"ORDERID": ["x"], "OrderID": ["y"]})
    out = run(df, rules, auto_normalise_aliases=False).raise_for_error().output(0)
    assert list(out.columns) == ["ORDERID", "order_id"] and out["order_id"].iloc[0] == "y"
    out = run(df, rules).raise_for_error().output(0)
    assert list(out.columns) == ["order_id"] and out["order_id"].iloc[0] == "x"


def test_blank_text_is_skipped_by_default(tmp_path):
    # Blank text in the first alias takes the next alias's value; the original's default left the blank in place
    rules = rules_file(tmp_path, "canonical,aliases\nname,First|Second\n")
    df = pd.DataFrame({"First": ["  ", "Ann"], "Second": ["Bob", "Cat"]})
    assert run(df, rules).raise_for_error().output(0)["name"].tolist() == ["Bob", "Ann"]
    out = run(df, rules, prefer_non_empty_strings=False).raise_for_error().output(0)
    assert out["name"].tolist() == ["  ", "Ann"]


def test_booleans_read_false_words_and_leave_unknowns_missing(tmp_path):
    # The original block turned anything not in its 'true' list, including missing and "maybe", into False
    rules = rules_file(tmp_path, "canonical,aliases,type\nok,OK,boolean\nflag,Flag,boolean\n")
    df = pd.DataFrame({"OK": ["Yes", "no", "FALSE", "maybe", None], "Flag": [1, 0, 1, None, 0]})
    res = run(df, rules).raise_for_error()
    out = res.output(0)
    assert out["ok"].tolist()[:3] == [True, False, False] and out["ok"].isna().tolist()[3:] == [True, True]
    assert out["flag"].tolist()[:3] == [True, False, True] and pd.isna(out["flag"].iloc[3])
    assert any("ok 1" in m for m in res.messages)


def test_date_fields_and_text_dates(tmp_path):
    rules = rules_file(tmp_path, "canonical,aliases,type,default,format\nday,Day|Date Text,date,,%d/%m/%Y\n"
                                 "stamp,Stamp,datetime,,\n")
    df = pd.DataFrame({"Day": pd.to_datetime(["2025-05-01", None]), "Date Text": ["x", "31/12/2024"],
                       "Stamp": pd.to_datetime(["2025-05-01 13:45", "2025-05-02 08:00"])})
    out = run(df, rules).raise_for_error().output(0)  # Date fields arrive time-zone aware
    assert out["day"].tolist() == [pd.Timestamp("2025-05-01", tz="UTC"), pd.Timestamp("2024-12-31", tz="UTC")]
    assert out["stamp"].iloc[0] == pd.Timestamp("2025-05-01 13:45", tz="UTC")


def test_integer_type_rejects_fractions_and_number_reads_numeric_text(tmp_path):
    rules = rules_file(tmp_path, "canonical,aliases,type\nn,N,integer\nx,X,number\n")
    df = pd.DataFrame({"N": ["3", "2.5", "4.0"], "X": ["1.25", "£3", "7"]})
    res = run(df, rules).raise_for_error()
    out = res.output(0)
    assert out["n"].tolist()[0] == 3 and pd.isna(out["n"].iloc[1]) and out["n"].iloc[2] == 4
    assert out["x"].iloc[0] == 1.25 and pd.isna(out["x"].iloc[1]) and out["x"].iloc[2] == 7.0
    assert any("n 1" in m and "x 1" in m for m in res.messages)


def test_comma_separated_aliases_and_rules_text_like_na(tmp_path):
    # "NA" and "null" in the rules file are names, not missing values
    rules = rules_file(tmp_path, 'canonical,aliases,type,default\nregion,"Area, Zone",string,NA\nnull,Nil,string,\n')
    df = pd.DataFrame({"Zone": ["North", None], "Nil": ["a", "b"]})
    out = run(df, rules).raise_for_error().output(0)
    assert list(out.columns) == ["region", "null"] and out["region"].tolist() == ["North", "NA"]


def test_empty_input(tmp_path):
    df = pd.DataFrame({"Qty": pd.Series([], dtype="float64"), "Client": pd.Series([], dtype=object)})
    out = run(df, add_missing_canonical=True).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == CANONICAL  # Client is an alias of customer
    assert str(out["quantity"].dtype) == "Int64" and pd.api.types.is_datetime64_any_dtype(out["order_date"])


def test_bad_rules_and_options_abort(tmp_path):
    df = pd.DataFrame({"a": [1]})
    res = run(df, rules=None)
    assert res.status == "aborted" and "schema rules file" in res.final_message
    res = run(df, rules=str(tmp_path / "missing.csv"))
    assert res.status == "aborted" and "not found" in res.final_message
    res = run(df, rules_file(tmp_path, "name,alias\na,b\n"))
    assert res.status == "aborted" and "canonical" in res.final_message
    res = run(df, rules_file(tmp_path, "canonical,aliases,type\na,b,money\n"))
    assert res.status == "aborted" and "Unknown type" in res.final_message
    res = run(df, rules_file(tmp_path, "canonical,aliases\na,b\na,c\n"))
    assert res.status == "aborted" and "twice" in res.final_message
    res = run(df, rules_file(tmp_path, "canonical,aliases,type,default\na,b,number,lots\n"))
    assert res.status == "aborted" and "not a valid number" in res.final_message
    res = run(df, rules_file(tmp_path, "canonical,aliases\n,b\n"))
    assert res.status == "aborted" and "no canonical" in res.final_message


def test_large_input():
    n = 100_000
    rng = np.random.default_rng(0)
    qty = rng.integers(1, 50, n).astype(float)
    qty[:20_000] = np.nan  # the first 20,000 records have no Qty: Units fills in
    df = pd.DataFrame({"OrderID": [f"O-{i}" for i in range(n)], "Qty": qty,
                       "Units": rng.integers(1, 50, n), "Unit Price": rng.uniform(1, 20, n).round(2),
                       "Date Ordered": ["2025-01-0%d" % (1 + i % 9) for i in range(n)]})
    t0 = time.time()
    out = run(df).raise_for_error().output(0)
    assert time.time() - t0 < 60
    assert len(out) == n and str(out["quantity"].dtype) == "Int64" and out["quantity"].notna().all()
    assert out["quantity"].iloc[0] == df["Units"].iloc[0] and out["quantity"].iloc[-1] == qty[-1]


# ---- Streaming: several chunks ----

def test_several_chunks_keep_one_schema_and_count_across_chunks(tmp_path):
    # The harness's stand-in calls the stream function once per 10,000 records, as Omniscope does chunk by chunk.
    # The second chunk has no usable dates or quantities at all; the schema must not change, and the message
    # counts the unreadable values of every chunk.
    rules = rules_file(tmp_path, "canonical,aliases,type,default,format\nqty,Qty,integer,,\n"
                                 "when,When,date,,%d/%m/%Y\nok,OK,boolean,,\n")
    n = 25_000
    qty = [str(i % 7) for i in range(n)]
    when = ["31/01/2025"] * n
    ok = (["yes", "no"] * n)[:n]
    for i in range(10_000, 20_000):
        qty[i], when[i], ok[i] = "n/k", None, None
    qty[20_000] = "2.5"
    df = pd.DataFrame({"Qty": qty, "When": when, "OK": ok, "Other": range(n)}, dtype=object)
    res = run(df, rules).raise_for_error()
    out = res.output(0)
    assert len(out) == n and list(out.columns) == ["qty", "when", "ok", "Other"]
    assert str(out["qty"].dtype) == "Int64" and out["qty"].isna().sum() == 10_001
    assert out["when"].notna().sum() == 15_000 and out["when"].iloc[-1] == pd.Timestamp("2025-01-31", tz="UTC")
    assert str(out["ok"].dtype) == "boolean" and out["ok"].isna().sum() == 10_000
    assert "qty 10001" in res.messages[-1]


# ---- Rules written in the block (the Schema rules text option) ----

SAMPLE_TEXT = ("order_id, OrderID|Order No; order_date, Order Date|OrderDate|Date Ordered, date, , %d/%m/%Y; "
               "customer, Customer Name|Client; sku, SKU|SKU Code|Product Code; quantity, Qty|Quantity|Units, integer; "
               "unit_price, Unit Price|Price, number; paid, Paid|Is Paid, boolean, false; currency, Currency, string, GBP")


def test_rules_text_gives_the_same_result_as_the_file():
    for data in (NORTH, SOUTH):
        from_file = run(data, add_missing_canonical=True).raise_for_error().output(0)
        from_text = run_block(HERE, data, {"rulesText": SAMPLE_TEXT, "add_missing_canonical": True})
        pd.testing.assert_frame_equal(from_text.raise_for_error().output(0), from_file)
    # The rules file itself, pasted with its heading row and one rule per line, gives the same result too
    with open(RULES, encoding="utf-8") as fh:
        pasted = fh.read().replace("\n", "\r\n")
    from_pasted = run_block(HERE, NORTH, {"rulesText": pasted, "add_missing_canonical": True}).raise_for_error()
    pd.testing.assert_frame_equal(from_pasted.output(0), run(NORTH, add_missing_canonical=True).output(0))


def test_rules_text_takes_precedence_over_the_file_and_blank_falls_back():
    out = run(NORTH, rulesText="client, Customer|Client").raise_for_error().output(0)
    assert "client" in out.columns and "order_id" not in out.columns
    out = run(NORTH, rulesText="  ").raise_for_error().output(0)
    assert "order_id" in out.columns


def test_rules_text_heading_quotes_and_short_rules():
    # A heading row in any order and case; quoted aliases with commas and semicolons; missing trailing cells
    text = 'Type,Canonical,Aliases\ninteger,qty,"Units; Count, Qty"\n'
    df = pd.DataFrame({"Qty": ["3"], "Name": ["a"]})
    out = run_block(HERE, df, {"rulesText": text}).raise_for_error().output(0)
    assert list(out.columns) == ["qty", "Name"] and out["qty"].tolist() == [3]
    out = run_block(HERE, df, {"rulesText": "name"}).raise_for_error().output(0)  # canonical only: exact name
    assert list(out.columns) == ["Qty", "name"]


def test_rules_text_mistakes_stop_with_a_message():
    df = pd.DataFrame({"a": [1]})
    res = run_block(HERE, df, {"rulesText": "a, b, number, 0, , extra"})
    assert res.status == "aborted" and "at most five" in res.final_message
    res = run_block(HERE, df, {"rulesText": "a, b, money"})
    assert res.status == "aborted" and "Unknown type" in res.final_message
    res = run_block(HERE, df, {"rulesText": "canonical,alias\na,b"})
    assert res.status == "aborted" and "Schema rules option" in res.final_message and "aliases" in res.final_message
    res = run_block(HERE, df, {})
    assert res.status == "aborted" and "Schema rules option" in res.final_message
