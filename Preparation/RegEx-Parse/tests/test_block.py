import os
import time

import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "order-notes.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"field": "t", **opts})


def notes():
    return pd.DataFrame({"t": ["Order #A-1 on 2025-03-04 via DHL", "order #b-22 via DPD", None, "nothing here"]})


def test_parse_named_groups_and_case():
    out = run(notes(), pattern=r"order #(?P<Order>[A-Z]-\d+).*?via (?P<Carrier>\w+)").raise_for_error().output(0)
    assert out["Order"].tolist()[:2] == ["A-1", "b-22"] and out["Carrier"].tolist()[:2] == ["DHL", "DPD"]
    assert pd.isna(out["Order"].iloc[2]) and pd.isna(out["Order"].iloc[3])
    strict = run(notes(), pattern=r"Order #([A-Z]-\d+)", ignore_case=False, output_names="Ref").raise_for_error().output(0)
    assert strict["Ref"].tolist()[0] == "A-1" and pd.isna(strict["Ref"].iloc[1])


def test_replace_with_backreference_both_styles():
    df = pd.DataFrame({"t": ["card 1234567812344242 ok", "none"]})
    a = run(df, mode="REPLACE", pattern=r"\d{12}(\d{4})", replacement=r"************\1").raise_for_error().output(0)
    b = run(df, mode="REPLACE", pattern=r"\d{12}(\d{4})", replacement="XXXX$1", output_field="masked").raise_for_error().output(0)
    assert a["t"].iloc[0] == "card ************4242 ok" and b["masked"].iloc[0] == "card XXXX4242 ok" and b["t"].iloc[0].startswith("card 1234")
    assert run(df, mode="REPLACE", pattern=r"(\d)", replacement=r"\2").status == "aborted"


def test_tokenise_columns_and_rows():
    df = pd.DataFrame({"t": ["SKU-1, SKU-22 and SKU-333", "no skus", "SKU-9"]})
    cols = run(df, mode="TOKENISE", pattern=r"SKU-\d+", max_columns=2).raise_for_error()
    o = cols.output(0)
    assert o["t 1"].tolist()[0] == "SKU-1" and o["t 2"].tolist()[0] == "SKU-22" and "more tokens" in cols.final_message
    rows = run(df, mode="TOKENISE", pattern=r"SKU-(\d+)", tokenise_to="ROWS", output_field="SKU Number").raise_for_error().output(0)
    assert rows["SKU Number"].tolist()[:3] == ["1", "22", "333"] and len(rows) == 5
    assert rows["Token Number"].tolist()[:3] == [1, 2, 3]
    dropped = run(df, mode="TOKENISE", pattern=r"SKU-\d+", tokenise_to="ROWS", keep_unmatched=False).raise_for_error().output(0)
    assert len(dropped) == 4


def test_match_modes():
    df = pd.DataFrame({"t": ["jane@example.com", "bad@@example.com", "x jane@example.com", None]})
    rx = r"[\w.+-]+@[\w-]+\.[\w.]+"
    full = run(df, mode="MATCH", pattern=rx, match_type="FULL", output_field="Valid Email").raise_for_error().output(0)
    assert full["Valid Email"].tolist()[:3] == ["Yes", "No", "No"] and pd.isna(full["Valid Email"].iloc[3])
    anywhere = run(df, mode="MATCH", pattern=rx).raise_for_error().output(0)
    assert anywhere["t Matches"].tolist()[:3] == ["Yes", "No", "Yes"]  # "@@" never matches; text around an address does


def test_sample_notes():
    res = run_block(HERE, SAMPLE, {"field": "Note", "pattern": r"order #(?P<Order>[A-Z]-\d+) shipped (?P<Shipped>\d{4}-\d{2}-\d{2}) via (?P<Carrier>[A-Za-z ]+?), tracking (?P<Tracking>\w+)"}).raise_for_error()
    out = res.output(0)
    assert out["Carrier"].notna().sum() == 6 and set(out["Carrier"].dropna()) == {"DHL", "Royal Mail", "DPD"}


def test_bad_inputs():
    assert run(notes(), pattern="(unclosed").status == "aborted"
    assert run(notes(), pattern="").status == "aborted"
    assert run(notes(), pattern=r"\d+").status == "aborted"  # parse needs a group
    assert run(notes(), field="nope", pattern="x").status == "aborted"
    out = run(pd.DataFrame({"t": [123, 45.5]}), mode="MATCH", pattern=r"^\d+$").raise_for_error().output(0)
    assert out["t Matches"].tolist() == ["Yes", "No"]
    assert len(run(notes().iloc[0:0], pattern=r"(\d)").raise_for_error().output(0)) == 0


def test_large_input_is_fast():
    df = pd.DataFrame({"t": ["Order #A-10234 shipped via DHL, SKU-1 SKU-2"] * 200_000})
    t0 = time.time()
    run(df, pattern=r"Order #(?P<Order>[A-Z]-\d+).*?via (?P<Carrier>\w+)").raise_for_error()
    run(df, mode="TOKENISE", pattern=r"SKU-\d+", tokenise_to="ROWS").raise_for_error()
    assert time.time() - t0 < 60
