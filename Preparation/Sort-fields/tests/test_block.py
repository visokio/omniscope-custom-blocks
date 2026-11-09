import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "survey-responses.csv")


def run(df, **options):
    return run_block(HERE, df, options).raise_for_error().output(0)


def test_sample_by_name_keeps_question_numbers_in_order():
    # The original sorted Q10 and Q11 before Q2
    out = run(SAMPLE, firstFields=["Respondent"])
    assert list(out.columns) == ["Respondent", "Q1 Region", "Q2 Age Band", "Q3 Visits Per Year", "Q4 Spend Per Visit",
                                 "Q10 Recommend Score", "Q11 Comment", "Submitted"]
    assert len(out) == 8
    src = pd.read_csv(SAMPLE)
    assert out["Q11 Comment"].tolist() == src["Q11 Comment"].tolist()  # values move with their field
    assert pd.api.types.is_datetime64_any_dtype(out["Submitted"])


def test_sample_by_type():
    # The original ordered by the pandas type name: Int64, datetime64, float64, then text
    out = run(SAMPLE, sortBy="type", firstFields=["Respondent"])
    assert list(out.columns) == ["Respondent", "Q1 Region", "Q2 Age Band", "Q11 Comment",
                                 "Q3 Visits Per Year", "Q4 Spend Per Visit", "Q10 Recommend Score", "Submitted"]


def test_name_sort_ignores_case():
    # The original put every capitalised name before every lower-case one
    df = pd.DataFrame({"banana": [1], "Apple": [2], "cherry": [3], "Date": [4]})
    assert list(run(df).columns) == ["Apple", "banana", "cherry", "Date"]


def test_first_fields_in_the_chosen_order():
    df = pd.DataFrame({"c": [1], "b": [2], "a": [3], "id": [4]})
    assert list(run(df, firstFields=["id", "c"]).columns) == ["id", "c", "a", "b"]
    assert list(run(df, firstFields=["missing"]).columns) == ["a", "b", "c", "id"]


def test_type_order_is_the_same_in_every_chunk():
    # An integer field that is all missing in one chunk arrives as decimal there; the order must not change
    n = 25_000
    df = pd.DataFrame({"z": np.arange(n, dtype=float), "a": ["x"] * n, "m": [1] * 10_000 + [None] * 15_000})
    df["m"] = df["m"].astype("Int64")
    out = run(df, sortBy="type")
    assert list(out.columns) == ["a", "m", "z"] and len(out) == n


def test_booleans_and_dates():
    df = pd.DataFrame({"flag": [True], "when": pd.to_datetime(["2025-01-01"]), "n": [1.5], "t": ["x"]})
    assert list(run(df, sortBy="type").columns) == ["t", "n", "when", "flag"]


def test_empty_input():
    df = pd.DataFrame({"b": pd.Series([], dtype=object), "a": pd.Series([], dtype="int64")})
    out = run(df)
    assert len(out) == 0 and list(out.columns) == ["a", "b"]


def test_bad_choice_aborts():
    res = run_block(HERE, pd.DataFrame({"a": [1]}), {"sortBy": "size"})
    assert res.status == "aborted" and "Sort fields by" in res.final_message


def test_large_input():
    n, k = 50_000, 200
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.normal(size=(n, k)), columns=[f"F{i}" for i in rng.permutation(k)])
    t0 = time.time()
    out = run(df)
    assert time.time() - t0 < 30
    assert list(out.columns) == [f"F{i}" for i in range(k)] and len(out) == n
