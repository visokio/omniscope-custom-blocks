import os
import time

import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "search-terms.csv")
OPTS = {"fieldName": "Search term"}


def encoded(df, field="Quoted text"):
    return dict(zip(df["Campaign"], df[field]))


def test_sample_terms_are_percent_encoded():
    out = run_block(HERE, SAMPLE, OPTS).raise_for_error().output(0)
    assert len(out) == 12
    assert list(out.columns) == ["Campaign", "Channel", "Search term", "Quoted text"]
    e = encoded(out)
    assert e["SPR-01"] == "caf%C3%A9%20cr%C3%A8me"            # UTF-8, spaces as %20
    assert e["SPR-02"] == "fish%20%26%20chips"                # & would end a query value
    assert e["SPR-03"] == "50%25%20off"                       # % itself is encoded
    assert e["SPR-04"] == "C%2B%2B%20for%20beginners"         # + would read as a space
    assert e["SPR-07"] == "Zo%C3%AB%27s%20%231%20pick"        # # would start a fragment
    assert e["SPR-08"] == "St%20Ives%20/%20Penzance"          # slashes kept by default
    assert e["SPR-12"] == "tea%20for%20two"


def test_missing_values_stay_missing():
    # The original script stopped with "quote_from_bytes() expected bytes" on the first empty value
    out = run_block(HERE, SAMPLE, OPTS).raise_for_error().output(0)
    assert pd.isna(encoded(out)["SPR-09"])
    out = run_block(HERE, pd.DataFrame({"t": [None, "a b", None]}), {"fieldName": "t"}).raise_for_error().output(0)
    assert pd.isna(out["Quoted text"].iloc[0]) and out["Quoted text"].iloc[1] == "a%20b"


def test_encode_slashes_and_spaces_as_plus():
    out = run_block(HERE, SAMPLE, {**OPTS, "encodeSlashes": True}).raise_for_error().output(0)
    assert encoded(out)["SPR-08"] == "St%20Ives%20%2F%20Penzance"
    out = run_block(HERE, SAMPLE, {**OPTS, "spacesAsPlus": True}).raise_for_error().output(0)
    e = encoded(out)
    assert e["SPR-12"] == "tea+for+two" and e["SPR-04"] == "C%2B%2B+for+beginners"
    assert e["SPR-08"] == "St+Ives+/+Penzance"
    out = run_block(HERE, SAMPLE, {**OPTS, "spacesAsPlus": True, "encodeSlashes": True}).raise_for_error().output(0)
    assert encoded(out)["SPR-08"] == "St+Ives+%2F+Penzance"


def test_output_field_name_and_replacing_in_place():
    out = run_block(HERE, SAMPLE, {**OPTS, "outputField": "Encoded term"}).raise_for_error().output(0)
    assert encoded(out, "Encoded term")["SPR-02"] == "fish%20%26%20chips"
    out = run_block(HERE, SAMPLE, {**OPTS, "outputField": "Search term"}).raise_for_error().output(0)
    assert list(out.columns) == ["Campaign", "Channel", "Search term"]
    assert encoded(out, "Search term")["SPR-02"] == "fish%20%26%20chips"
    out = run_block(HERE, SAMPLE, {**OPTS, "outputField": "  "}).raise_for_error().output(0)
    assert "Quoted text" in out.columns  # a blank name falls back to the default


def test_a_name_clash_with_another_field_aborts():
    # The original script silently overwrote an input field called "Quoted text"
    df = pd.DataFrame({"t": ["a b"], "Quoted text": ["keep me"]})
    res = run_block(HERE, df, {"fieldName": "t"})
    assert res.status == "aborted" and "already has a field" in res.final_message


def test_numbers_in_a_text_field_are_encoded_as_text():
    df = pd.DataFrame({"t": pd.Series(["12", "3 4", None], dtype=object)})
    out = run_block(HERE, df, {"fieldName": "t"}).raise_for_error().output(0)
    assert out["Quoted text"].tolist()[:2] == ["12", "3%204"]
    out = run_block(HERE, pd.DataFrame({"n": [1.5, 2.0]}), {"fieldName": "n"}).raise_for_error().output(0)
    assert out["Quoted text"].tolist() == ["1.5", "2.0"]


def test_empty_input_no_field_and_no_input():
    df = pd.DataFrame({"t": pd.Series([], dtype=object)})
    out = run_block(HERE, df, {"fieldName": "t"}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["t", "Quoted text"]
    res = run_block(HERE, pd.DataFrame({"t": ["x"]}), {"fieldName": None})
    assert res.status == "aborted" and "Choose the field" in res.final_message
    res = run_block(HERE, pd.DataFrame({"t": ["x"]}), {"fieldName": "missing"})
    assert res.status == "aborted" and "not in the input" in res.final_message
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted"


def test_large_input_in_chunks():
    n = 200_000
    df = pd.DataFrame({"id": range(n), "t": [f"item {i} & co/é" for i in range(n)]})
    t0 = time.time()
    out = run_block(HERE, df, {"fieldName": "t"}).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert len(out) == n and out["Quoted text"].iloc[-1] == "item%20199999%20%26%20co/%C3%A9"
