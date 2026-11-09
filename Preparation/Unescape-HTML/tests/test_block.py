import os
import time

import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "product-feed.csv")
OPTS = {"fieldName": "Title"}


def by_sku(df, field="Unicode text"):
    return dict(zip(df["SKU"], df[field]))


def test_sample_titles_are_unescaped():
    out = run_block(HERE, SAMPLE, OPTS).raise_for_error().output(0)
    assert len(out) == 12
    assert list(out.columns) == ["SKU", "Category", "Title", "Unicode text"]
    t = by_sku(out)
    assert t["HB-101"] == "Café mugs & saucers (set of 4)"
    assert t["HB-102"] == "Cast iron pan – 28 cm"           # &ndash; and &nbsp; (as a plain space)
    assert t["HB-103"] == 'Bird feeder "Robin"'
    assert t["HB-104"] == "Plant pots – terracotta"         # decimal reference
    assert t["HB-105"] == "Wool throw £45 → £39"
    assert t["HB-108"] == "Reading lamp <LED>"                   # tags are not removed
    assert t["HB-110"] == "R&D sample cushion"                   # not a reference: unchanged
    assert t["HB-111"] == "Espresso cups ☕ x2"              # hexadecimal reference
    assert t["HB-107"] == "Tea towels &amp; oven glove"          # double-escaped: one pass by default


def test_missing_values_stay_missing():
    # The original script stopped with "argument of type 'float' is not iterable" on the first empty value
    out = run_block(HERE, SAMPLE, OPTS).raise_for_error().output(0)
    assert pd.isna(by_sku(out)["HB-109"])


def test_repeat_for_double_escaped_text():
    out = run_block(HERE, SAMPLE, {**OPTS, "repeat": True}).raise_for_error().output(0)
    assert by_sku(out)["HB-107"] == "Tea towels & oven glove"
    df = pd.DataFrame({"t": ["&amp;amp;amp;lt;b&amp;amp;amp;gt;", "&amp;"]})
    out = run_block(HERE, df, {"fieldName": "t", "repeat": True}).raise_for_error().output(0)
    assert out["Unicode text"].tolist() == ["<b>", "&"]


def test_non_breaking_spaces():
    # The original kept U+00A0, which looks like a space but does not match one in a join or filter
    out = run_block(HERE, SAMPLE, OPTS).raise_for_error().output(0)
    assert " " not in "".join(out["Unicode text"].dropna())
    out = run_block(HERE, SAMPLE, {**OPTS, "plainSpaces": False}).raise_for_error().output(0)
    assert by_sku(out)["HB-112"] == "Hose 15 m & reel"


def test_output_field_name_and_replacing_in_place():
    out = run_block(HERE, SAMPLE, {**OPTS, "outputField": "Clean title"}).raise_for_error().output(0)
    assert by_sku(out, "Clean title")["HB-106"] == "Crème linen cushion"
    out = run_block(HERE, SAMPLE, {**OPTS, "outputField": "Title"}).raise_for_error().output(0)
    assert list(out.columns) == ["SKU", "Category", "Title"]
    assert by_sku(out, "Title")["HB-106"] == "Crème linen cushion"


def test_a_name_clash_with_another_field_aborts():
    # The original script silently overwrote an input field called "Unicode text"
    df = pd.DataFrame({"t": ["&amp;"], "Unicode text": ["keep me"]})
    res = run_block(HERE, df, {"fieldName": "t"})
    assert res.status == "aborted" and "already has a field" in res.final_message


def test_legacy_references_without_a_semicolon():
    # Python's html.unescape follows the HTML5 rules, as browsers do: some old names work without ";"
    df = pd.DataFrame({"t": ["&pound10", "Fish &chips", "&bogus;", "AT&T"]})
    out = run_block(HERE, df, {"fieldName": "t"}).raise_for_error().output(0)
    assert out["Unicode text"].tolist() == ["£10", "Fish &chips", "&bogus;", "AT&T"]


def test_empty_input_no_field_and_non_text_values():
    df = pd.DataFrame({"t": pd.Series([], dtype=object)})
    out = run_block(HERE, df, {"fieldName": "t"}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["t", "Unicode text"]
    res = run_block(HERE, pd.DataFrame({"t": ["x"]}), {"fieldName": None})
    assert res.status == "aborted" and "Choose the field" in res.final_message
    res = run_block(HERE, pd.DataFrame({"t": ["x"]}), {"fieldName": "missing"})
    assert res.status == "aborted" and "not in the input" in res.final_message
    out = run_block(HERE, pd.DataFrame({"n": [1.5, None]}), {"fieldName": "n"}).raise_for_error().output(0)
    assert out["Unicode text"].iloc[0] == "1.5" and pd.isna(out["Unicode text"].iloc[1])
    assert run_block(HERE, None, OPTS).status == "aborted"


def test_large_input_in_chunks():
    n = 200_000
    df = pd.DataFrame({"id": range(n), "t": [f"Item {i} &amp; caf&eacute;&nbsp;bar" for i in range(n)]})
    t0 = time.time()
    out = run_block(HERE, df, {"fieldName": "t"}).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert len(out) == n and out["Unicode text"].iloc[-1] == "Item 199999 & café bar"
