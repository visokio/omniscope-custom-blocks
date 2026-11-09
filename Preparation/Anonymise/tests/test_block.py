import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "customers.csv")
DEMO = {
    "selectedFields": ["Customer ID", "Name", "Email", "Signup Date", "Orders", "Lifetime Spend"],
    "sensitivity_date": 432000.0,  # 5 days; with budget 5, a typical shift of a day
}


def sample():
    return pd.read_csv(SAMPLE, dtype=str)


def test_sample_demo_settings():
    res = run_block(HERE, SAMPLE, DEMO).raise_for_error()
    out = res.output(0)
    raw = sample()
    assert len(out) == 20
    assert list(out.columns) == list(raw.columns)
    # fields not chosen are unchanged
    assert out["City"].tolist() == raw["City"].tolist() and out["Segment"].tolist() == raw["Segment"].tolist()
    # chosen text fields: every value replaced, distinct counts kept, the two Harriet Ellisons share a code word
    assert not set(out["Name"]) & set(raw["Name"])
    assert out["Name"].nunique() == raw["Name"].nunique() == 19
    assert out["Name"].iloc[0] == out["Name"].iloc[7]
    assert out["Customer ID"].nunique() == 20
    assert out["Name"].str.fullmatch(r"[a-z]+\d+").all()
    # missing values stay missing
    assert pd.isna(out["Email"].iloc[13]) and out["Email"].notna().sum() == 19
    assert pd.isna(out["Orders"].iloc[14]) and pd.isna(out["Lifetime Spend"].iloc[14])
    assert pd.isna(out["Signup Date"].iloc[16])
    # types kept: whole numbers stay whole numbers, dates stay dates
    assert str(out["Orders"].dtype) == "Int64"
    assert pd.api.types.is_float_dtype(out["Lifetime Spend"])
    assert pd.api.types.is_datetime64_any_dtype(out["Signup Date"])
    # values moved, but not far
    spend = raw["Lifetime Spend"].astype(float)
    assert (out["Lifetime Spend"] - spend).abs().max() < 50
    assert ((out["Lifetime Spend"] != spend) & spend.notna()).sum() == 19


def test_defaults_anonymise_every_field():
    out = run_block(HERE, SAMPLE, {}).raise_for_error().output(0)
    raw = sample()
    assert not set(out["City"].dropna()) & set(raw["City"])
    # a code word is shared by the same value in different fields
    assert len(out) == 20


def test_same_value_same_word_across_fields():
    df = pd.DataFrame({"From": ["Leeds", "York", "Leeds"], "To": ["York", "Hull", "Leeds"]})
    out = run_block(HERE, df, {}).raise_for_error().output(0)
    assert out["From"].iloc[0] == out["From"].iloc[2] == out["To"].iloc[2]
    assert out["From"].iloc[1] == out["To"].iloc[0]


def test_noise_size_follows_sensitivity_over_budget():
    n = 20_000
    df = pd.DataFrame({"x": np.zeros(n), "d": pd.Timestamp("2025-01-01") + pd.to_timedelta(np.zeros(n), unit="s")})
    out = run_block(HERE, df, {"sensitivity_numeric": 40.0, "epsilon_numeric": 4.0,
                               "sensitivity_date": 86400.0, "epsilon_date": 1.0}).raise_for_error().output(0)
    # Laplace(scale b): mean absolute value b
    assert 9 < out["x"].abs().mean() < 11
    shift = (out["d"] - pd.Timestamp("2025-01-01", tz="UTC")).dt.total_seconds().abs().mean()
    assert 0.9 * 86400 < shift < 1.1 * 86400


def test_integer_fields_stay_integer():
    # The original block turned whole-number fields into decimals (31.121066 orders)
    df = pd.DataFrame({"Orders": [3, None, 12, 40]})  # arrives as nullable Int64
    out = run_block(HERE, df, {}).raise_for_error().output(0)
    assert str(out["Orders"].dtype) == "Int64"
    assert pd.isna(out["Orders"].iloc[1]) and out["Orders"].notna().sum() == 3


def test_empty_input_keeps_text_fields_text():
    # The original block turned an empty text field into a decimal field
    df = pd.DataFrame({"Name": pd.Series([], dtype=object), "n": pd.Series([], dtype="float64")})
    out = run_block(HERE, df, {}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["Name", "n"]
    assert not pd.api.types.is_float_dtype(out["Name"])


def test_all_missing_text_field_stays_text():
    df = pd.DataFrame({"Name": pd.Series([None, None], dtype=object), "k": ["a", "b"]})
    out = run_block(HERE, df, {"selectedFields": ["Name"]}).raise_for_error().output(0)
    assert out["Name"].isna().all() and not pd.api.types.is_float_dtype(out["Name"])
    assert out["k"].tolist() == ["a", "b"]


def test_no_input_and_bad_options_abort_with_a_message():
    # The original block raised AttributeError / ValueError instead
    res = run_block(HERE, None, {})
    assert res.status == "aborted" and "Connect" in res.final_message
    for opts in ({"epsilon_numeric": 0.0}, {"epsilon_date": -1.0}):
        res = run_block(HERE, SAMPLE, opts)
        assert res.status == "aborted" and "budget" in res.final_message
    res = run_block(HERE, SAMPLE, {"sensitivity_date": 0.0})
    assert res.status == "aborted" and "sensitivit" in res.final_message


def test_other_types_pass_through():
    df = pd.DataFrame({"flag": [True, False], "n": [1.5, 2.5]})
    out = run_block(HERE, df, {"selectedFields": ["n"]}).raise_for_error().output(0)
    assert out["flag"].tolist() == [True, False]
    out = run_block(HERE, df, {"selectedFields": ["Not there"]}).raise_for_error().output(0)
    assert out["n"].tolist() == [1.5, 2.5]


def test_large_input():
    n = 200_000
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"name": [f"person {i % 20000}" for i in range(n)], "amount": rng.normal(100, 20, n),
                       "count": rng.integers(0, 50, n),
                       "when": pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 10**7, n), unit="s")})
    t0 = time.time()
    out = run_block(HERE, df, {}).raise_for_error().output(0)
    assert time.time() - t0 < 60
    assert len(out) == n and out["name"].nunique() == 20000


def test_code_words_use_british_spelling():
    """The code words appear in every output, so they follow British spelling (the list had analyze, behavior,
    favorable, organization and zucchini)."""
    import ast
    with open(os.path.join(HERE, "script.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    words = next(ast.literal_eval(n.value) for n in tree.body
                 if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "BASE_WORDS")
    american = {"analyze", "behavior", "favorable", "organization", "zucchini", "color", "center", "favor"}
    assert not american & set(words)
    assert not [w for w in words if w.endswith(("ize", "izes", "ization", "yze"))]
    assert {"analyse", "behaviour", "favourable", "organisation"} <= set(words)
