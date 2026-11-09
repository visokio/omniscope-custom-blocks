import json
import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "web-events.csv")
NEW_FIELDS = ["page", "referrer", "device", "sku", "qty", "price", "order_id", "items", "total", "voucher",
              "delivery", "query", "results", "gift"]


def run(df, **options):
    return run_block(HERE, df, options).raise_for_error()


def test_sample_events():
    res = run(SAMPLE, jsonField="Properties")
    out = res.output(0)
    assert len(out) == 12
    assert list(out.columns) == ["Event ID", "Timestamp", "Event", "Properties"] + NEW_FIELDS
    assert str(out["qty"].dtype) == "Int64" and out["qty"].sum() == 3
    assert pd.api.types.is_float_dtype(out["price"]) and out["total"].sum() == 91.47
    assert out.loc[2, "delivery"] == '{"method": "standard", "days": 3}'   # nested object as JSON text
    assert pd.isna(out.loc[2, "voucher"]) and out.loc[10, "voucher"] == "SUMMER10"
    assert out["gift"].tolist()[5] is True or out["gift"].tolist()[5] == True  # noqa: E712
    assert out["device"].notna().sum() == 9
    # E-1007 (empty), E-1010 (broken JSON) and E-1012 (an array) keep their record with empty new fields
    assert out.loc[[6, 9, 11], NEW_FIELDS].isna().all().all()
    assert "2 record(s)" in res.final_message
    assert pd.api.types.is_datetime64_any_dtype(out["Timestamp"])  # input fields keep their types


def test_json_that_is_not_an_object_no_longer_aborts():
    # The original aborted the whole block on one record holding a JSON array or a number
    df = pd.DataFrame({"id": [1, 2, 3], "j": ['{"a": 1}', "[1, 2]", "42"]})
    out = run(df, jsonField="j").output(0)
    assert out["a"].tolist()[0] == 1 and out["a"].isna().sum() == 2


def test_nested_values_become_json_text():
    # The original wrote Python's repr ({'x': 1}), which is not JSON
    df = pd.DataFrame({"j": ['{"o": {"x": 1, "s": "é"}, "l": [1, "two", null]}']})
    out = run(df, jsonField="j").output(0)
    assert json.loads(out["o"].iloc[0]) == {"x": 1, "s": "é"} and out["o"].iloc[0] == '{"x": 1, "s": "é"}'
    assert json.loads(out["l"].iloc[0]) == [1, "two", None]


def test_mixed_types_in_one_key_become_text():
    df = pd.DataFrame({"j": ['{"v": 12}', '{"v": "many"}', '{"v": true}', '{"v": 1.5}']})
    out = run(df, jsonField="j").output(0)
    assert out["v"].tolist() == ["12", "many", "true", "1.5"]
    out = run(pd.DataFrame({"j": ['{"v": 1}', '{"v": 2.5}']}), jsonField="j").output(0)
    assert out["v"].tolist() == [1.0, 2.5]


def test_prefix_and_without_input_fields():
    df = pd.DataFrame({"id": [1, 2], "j": ['{"a": "x", "b": 2}', '{"a": "y"}']})
    out = run(df, jsonField="j", fieldPrefix="p_", includeInput=False).output(0)
    assert list(out.columns) == ["p_a", "p_b"] and out["p_a"].tolist() == ["x", "y"]


def test_key_clashing_with_an_input_field_aborts_with_advice():
    # The original wrote two fields called "id", which fails
    df = pd.DataFrame({"id": [1], "j": ['{"id": 99, "a": 1}']})
    res = run_block(HERE, df, {"jsonField": "j"})
    assert res.status == "aborted" and "id" in res.final_message and "Prefix" in res.final_message
    assert run(df, jsonField="j", fieldPrefix="json_").output(0)["json_id"].tolist() == [99]


def test_empty_input_still_writes_the_fields():
    # The original wrote nothing for an empty input
    df = pd.DataFrame({"id": pd.Series([], dtype="int64"), "j": pd.Series([], dtype=object)})
    out = run(df, jsonField="j").output(0)
    assert out is not None and len(out) == 0 and list(out.columns) == ["id", "j"]


def test_number_field_and_bad_options():
    df = pd.DataFrame({"n": [1, 2]})
    res = run_block(HERE, df, {"jsonField": "n", "includeInput": False})
    assert res.status == "aborted" and "No JSON objects" in res.final_message
    out = run(df, jsonField="n").output(0)
    assert list(out.columns) == ["n"]
    res = run_block(HERE, df, {"jsonField": None})
    assert res.status == "aborted" and "Choose" in res.final_message
    assert run_block(HERE, None, {"jsonField": "n"}).status == "aborted"


def test_large_input():
    n = 100_000
    rng = np.random.default_rng(0)
    qty = rng.integers(1, 10, n)
    df = pd.DataFrame({"id": np.arange(n),
                       "j": [json.dumps({"sku": f"S{i % 500}", "qty": int(q), "price": round(float(i % 97) + 0.5, 2),
                                         "tags": ["a", "b"]}) for i, q in enumerate(qty)]})
    t0 = time.time()
    out = run(df, jsonField="j").output(0)
    assert time.time() - t0 < 30
    assert len(out) == n and int(out["qty"].sum()) == int(qty.sum())
