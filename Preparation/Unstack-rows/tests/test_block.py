import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "stacked-orders.csv")
BOTH = {"textFields": ["Products", "Quantities"]}


def test_sample_orders_unstack_to_one_record_per_product():
    out = run_block(HERE, SAMPLE, BOTH).raise_for_error().output(0)
    assert len(out) == 21
    assert list(out.columns) == ["Order", "Customer", "Order Date", "Products", "Quantities"]
    first = out[out["Order"] == "SO-2001"]
    assert first["Products"].tolist() == ["Terracotta pot 30cm", "Compost 50L", "Hand trowel"]
    assert first["Quantities"].tolist() == ["12", "20", "6"]
    assert set(first["Customer"]) == {"Fernhill Garden Centre"}
    # fewer quantities than products: the missing quantity is empty text
    assert out.loc[out["Products"] == "Cane bundle", "Quantities"].tolist() == [""]
    # an order with no products is kept, once
    assert (out["Order"] == "SO-2007").sum() == 1
    # other fields keep their types
    assert pd.api.types.is_datetime64_any_dtype(out["Order Date"])


def test_one_field_only_repeats_the_others():
    out = run_block(HERE, SAMPLE, {"textFields": ["Products"]}).raise_for_error().output(0)
    assert len(out) == 21
    assert out.loc[out["Order"] == "SO-2001", "Quantities"].tolist() == ["12\n20\n6"] * 3


def test_other_separators_and_escapes():
    df = pd.DataFrame({"id": [1, 2], "tags": ["a,b,c", "d"], "tabbed": ["x\ty", "z"]})
    out = run_block(HERE, df, {"textFields": ["tags"], "separator": ","}).raise_for_error().output(0)
    assert out["tags"].tolist() == ["a", "b", "c", "d"] and out["id"].tolist() == [1, 1, 1, 2]
    out = run_block(HERE, df, {"textFields": ["tabbed"], "separator": "\\t"}).raise_for_error().output(0)
    assert out["tabbed"].tolist() == ["x", "y", "z"]
    out = run_block(HERE, df, {"textFields": ["tags"], "separator": ", "}).raise_for_error().output(0)
    assert out["tags"].tolist() == ["a,b,c", "d"]  # the separator is matched exactly


def test_records_with_only_missing_values_are_kept():
    # The original block dropped a record whose chosen fields were all missing
    df = pd.DataFrame({"id": [1, 2, 3], "a": ["p\nq", None, "r"], "b": [None, None, "s\nt"]})
    out = run_block(HERE, df, {"textFields": ["a", "b"]}).raise_for_error().output(0)
    assert out["id"].tolist() == [1, 1, 2, 3, 3]
    assert out["a"].tolist()[:2] == ["p", "q"] and pd.isna(out["b"].iloc[0]) and out["b"].iloc[1] == ""
    assert pd.isna(out["a"].iloc[2]) and out["b"].tolist()[3:] == ["s", "t"] and out["a"].tolist()[3:] == ["r", ""]


def test_integer_fields_keep_their_type():
    df = pd.DataFrame({"id": [1, None, 3], "a": ["x\ny", "z", "w"]})  # id arrives as nullable Int64
    out = run_block(HERE, df, {"textFields": ["a"]}).raise_for_error().output(0)
    assert str(out["id"].dtype) == "Int64" and out["id"].tolist()[:2] == [1, 1]


def test_empty_input():
    df = pd.DataFrame({"id": pd.Series([], dtype="int64"), "a": pd.Series([], dtype=object)})
    out = run_block(HERE, df, {"textFields": ["a"]}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["id", "a"]


def test_non_text_fields_pass_through_and_bad_options_abort():
    df = pd.DataFrame({"id": [1, 2], "n": [1.5, 2.5]})
    out = run_block(HERE, df, {"textFields": ["n"]}).raise_for_error().output(0)
    assert out["n"].tolist() == [1.5, 2.5] and out["id"].tolist() == [1, 2]
    res = run_block(HERE, df, {"textFields": None})
    assert res.status == "aborted" and "Choose" in res.final_message
    res = run_block(HERE, pd.DataFrame({"a": ["x"]}), {"textFields": ["a"], "separator": ""})
    assert res.status == "aborted" and "separator" in res.final_message
    assert run_block(HERE, None, BOTH).status == "aborted"


def test_large_input_is_fast():
    n = 200_000
    rng = np.random.default_rng(0)
    k = rng.integers(1, 6, n)
    df = pd.DataFrame({"id": np.arange(n), "v": rng.normal(size=n),
                       "items": ["\n".join(f"item{j}" for j in range(m)) for m in k]})
    t0 = time.time()
    out = run_block(HERE, df, {"textFields": ["items"]}).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert len(out) == int(k.sum())


def test_input_with_only_the_chosen_field():
    # The original block raised "Length of indexer and values mismatch" here
    out = run_block(HERE, pd.DataFrame({"tags": ["a,b,c", "d"]}), {"textFields": ["tags"], "separator": ","})
    assert out.raise_for_error().output(0)["tags"].tolist() == ["a", "b", "c", "d"]
