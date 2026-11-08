import json
import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "orders-with-lines.csv")
JSON_FIELDS = ["Lines_sku", "Lines_name", "Lines_qty", "Lines_price", "Lines_options.colour", "Lines_tags"]


def run(df, **options):
    return run_block(HERE, df, options).raise_for_error()


def test_sample_orders_to_order_lines():
    res = run(SAMPLE, jsonField="Lines")
    out = res.output(0)
    assert len(out) == 12
    assert list(out.columns) == ["Order", "Customer", "Order Date", "Lines"] + JSON_FIELDS
    assert out.loc[out["Order"] == "SO-3003", "Lines_sku"].tolist() == ["NT-04", "CB-10", "HT-02"]
    assert str(out["Lines_qty"].dtype) == "Int64" and out["Lines_qty"].sum() == 140
    assert round(float((out["Lines_qty"].astype("float64") * out["Lines_price"]).sum()), 2) == 892.0
    assert out.loc[out["Lines_sku"] == "HR-01", "Lines_options.colour"].tolist() == ["green"]
    assert out.loc[out["Order"] == "SO-3007", "Lines_tags"].tolist() == ['["bulk", "pallet"]']  # array as JSON text
    # SO-3005 holds a single object (one line); SO-3004 is empty and SO-3008 is broken JSON: kept once each
    assert (out["Order"] == "SO-3005").sum() == 1
    kept = out[out["Order"].isin(["SO-3004", "SO-3008"])]
    assert len(kept) == 2 and kept[JSON_FIELDS].isna().all().all()
    assert "1 record(s)" in res.final_message
    assert pd.api.types.is_datetime64_any_dtype(out["Order Date"])  # input fields keep their types


def test_invalid_json_no_longer_fails_the_block():
    # The original raised JSONDecodeError for one bad record
    df = pd.DataFrame({"id": [1, 2], "j": ['{"a": 1}', '{"a": ']})
    out = run(df, jsonField="j").output(0)
    assert out["id"].tolist() == [1, 2] and out["j_a"].tolist()[0] == 1 and pd.isna(out["j_a"].iloc[1])


def test_input_field_types_are_kept():
    # The original copied input values row by row, turning Int64 fields into object
    df = pd.DataFrame({"id": [1, None, 3], "j": ['[{"a": 1}, {"a": 2}]', '{"a": 3}', '{"a": 4}']})
    out = run(df, jsonField="j").output(0)
    assert str(out["id"].dtype) == "Int64" and out["id"].tolist()[:2] == [1, 1] and pd.isna(out["id"].iloc[2])


def test_records_without_json_are_kept_with_input_fields_and_dropped_without():
    df = pd.DataFrame({"id": [1, 2, 3], "j": ['{"a": 1}', None, "[]"]})
    out = run(df, jsonField="j").output(0)
    assert out["id"].tolist() == [1, 2, 3]
    out = run(df, jsonField="j", includeInput=False).output(0)
    assert list(out.columns) == ["j_a"] and out["j_a"].tolist() == [1]


def test_arrays_of_values_and_scalars():
    df = pd.DataFrame({"j": ['["red", "blue"]', "5"]})
    out = run(df, jsonField="j").output(0)
    assert out["j_value"].tolist() == ["red", "blue", "5"]  # mixed text and number: text


def test_nested_objects_and_mixed_types():
    df = pd.DataFrame({"j": ['{"c": {"name": "A", "geo": {"lat": 51.5}}, "n": 1}',
                             '{"c": {"name": "B"}, "n": "two", "flag": true}']})
    out = run(df, jsonField="j").output(0)
    assert list(out.columns) == ["j", "j_c.name", "j_c.geo.lat", "j_n", "j_flag"]
    assert out["j_c.geo.lat"].tolist()[0] == 51.5 and out["j_n"].tolist() == ["1", "two"]


def test_empty_input():
    # The original failed with "No objects to concatenate"
    df = pd.DataFrame({"id": pd.Series([], dtype="int64"), "j": pd.Series([], dtype=object)})
    out = run(df, jsonField="j").output(0)
    assert len(out) == 0 and list(out.columns) == ["id", "j"]


def test_bad_options_and_no_json():
    df = pd.DataFrame({"n": [1, 2]})
    res = run_block(HERE, df, {"jsonField": "n", "includeInput": False})
    assert res.status == "aborted" and "No JSON" in res.final_message
    res = run_block(HERE, df, {"jsonField": None})
    assert res.status == "aborted" and "Choose" in res.final_message
    assert run_block(HERE, None, {"jsonField": "n"}).status == "aborted"


def test_large_input():
    n = 20_000
    rng = np.random.default_rng(0)
    k = rng.integers(1, 6, n)
    df = pd.DataFrame({"order": np.arange(n),
                       "lines": [json.dumps([{"sku": f"S{j}", "qty": int(j + 1), "opt": {"size": "M"}}
                                             for j in range(m)]) for m in k]})
    t0 = time.time()
    out = run(df, jsonField="lines").output(0)
    assert time.time() - t0 < 30
    assert len(out) == int(k.sum()) and str(out["lines_qty"].dtype) == "Int64"
