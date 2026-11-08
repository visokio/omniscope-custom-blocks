import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "feedback-cards.csv")
COLUMNS = ["Received", "Branch", "Rating", "Comment"]


def test_sample_cards_are_numbered_in_order():
    out = run_block(HERE, SAMPLE).raise_for_error().output(0)
    assert len(out) == 15
    assert list(out.columns) == COLUMNS + ["Row ID"]
    assert out["Row ID"].tolist() == list(range(1, 16))
    assert pd.api.types.is_integer_dtype(out["Row ID"])
    assert out.loc[out["Row ID"] == 10, "Comment"].item() == "Cold food"
    # the other fields keep their values and types
    assert pd.api.types.is_datetime64_any_dtype(out["Received"])
    assert out["Rating"].tolist()[:3] == [5, 3, 4]


def test_name_start_and_first_position():
    out = run_block(HERE, SAMPLE, {"fieldName": "Card No", "startAt": 1001, "putFirst": True}).raise_for_error().output(0)
    assert list(out.columns) == ["Card No"] + COLUMNS
    assert out["Card No"].tolist()[:2] == [1001, 1002] and out["Card No"].iloc[-1] == 1015
    out = run_block(HERE, SAMPLE, {"startAt": 0}).raise_for_error().output(0)
    assert out["Row ID"].tolist()[:2] == [0, 1]


def test_empty_or_blank_name_gives_row_id():
    # The original named the field "None" when the option was cleared, and " " when it was a space
    for name in (None, "", "   "):
        out = run_block(HERE, SAMPLE, {"fieldName": name}).raise_for_error().output(0)
        assert list(out.columns) == COLUMNS + ["Row ID"]
    out = run_block(HERE, SAMPLE, {"fieldName": "  Seq  "}).raise_for_error().output(0)
    assert list(out.columns) == COLUMNS + ["Seq"]


def test_existing_field_of_the_same_name_is_replaced():
    df = pd.DataFrame({"Row ID": ["a", "b"], "x": [1, 2]})
    out = run_block(HERE, df).raise_for_error().output(0)
    assert list(out.columns) == ["Row ID", "x"] and out["Row ID"].tolist() == [1, 2]
    df = pd.DataFrame({"x": [1, 2], "Row ID": [9, 9]})
    out = run_block(HERE, df, {"putFirst": True}).raise_for_error().output(0)
    assert list(out.columns) == ["Row ID", "x"] and out["Row ID"].tolist() == [1, 2]


def test_numbers_run_on_across_chunks():
    # The stand-in calls the stream function once per 10,000 records, as Omniscope passes the data chunk by chunk;
    # the count carries on between chunks, so the IDs have no gaps or repeats.
    n = 25_001
    df = pd.DataFrame({"x": np.arange(n), "Row ID": ["old"] * n})
    out = run_block(HERE, df, {"startAt": 1001, "putFirst": True}).raise_for_error().output(0)
    assert list(out.columns) == ["Row ID", "x"] and len(out) == n
    assert out["Row ID"].tolist() == list(range(1001, 1001 + n))
    assert (out["Row ID"] - out["x"] == 1001).all()  # each record keeps its own number
    out = run_block(HERE, df.drop(columns="Row ID")).raise_for_error().output(0)
    assert out["Row ID"].iloc[[0, 9_999, 10_000, -1]].tolist() == [1, 10_000, 10_001, n]


def test_empty_input():
    df = pd.DataFrame({"a": pd.Series([], dtype=object), "n": pd.Series([], dtype="float64")})
    out = run_block(HERE, df).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["a", "n", "Row ID"]
    assert pd.api.types.is_integer_dtype(out["Row ID"])


def test_bad_options():
    res = run_block(HERE, SAMPLE, {"startAt": "ten"})
    assert res.status == "aborted" and "whole number" in res.final_message
    # a text start that is a whole number is accepted
    out = run_block(HERE, SAMPLE, {"startAt": "5"}).raise_for_error().output(0)
    assert out["Row ID"].iloc[0] == 5


def test_any_field_types_pass_through():
    df = pd.DataFrame({"t": ["a", None], "i": [1, None], "b": [True, False],
                       "d": pd.to_datetime(["2025-01-01", None]).tz_localize("UTC")})
    out = run_block(HERE, df).raise_for_error().output(0)
    assert str(out["i"].dtype) == "Int64" and out["Row ID"].tolist() == [1, 2]
    assert str(out["d"].dtype).endswith("UTC]")


def test_large_input():
    n = 1_000_000
    df = pd.DataFrame({"v": np.random.default_rng(0).normal(size=n)})
    t0 = time.time()
    out = run_block(HERE, df).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert out["Row ID"].iloc[-1] == n and (out["Row ID"].diff().iloc[1:] == 1).all()
