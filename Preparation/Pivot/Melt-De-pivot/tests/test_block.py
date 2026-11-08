import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "store-sales-wide.csv")
FIXED = {"fixed_fields": ["Store", "Region"]}


def melt(data, **options):
    return run_block(HERE, [data], options).raise_for_error().output(0)


def test_sample():
    res = run_block(HERE, [SAMPLE], FIXED).raise_for_error()
    out = res.output(0)
    assert list(out.columns) == ["Store", "Region", "Field", "Value"]
    assert len(out) == 24
    assert str(out["Value"].dtype) == "Int64"  # all four months are whole numbers
    harbour = out[out["Store"] == "Harbour Street"]
    assert harbour["Field"].tolist() == ["Jan", "Feb", "Mar", "Apr"]
    assert harbour["Value"].tolist() == [12400, 11850, 13900, 14250]
    assert res.final_message == "6 records x 4 fields de-pivoted: 24 records"


def test_each_record_comes_out_together_in_field_order():
    out = melt(SAMPLE, **FIXED)
    assert out["Store"].tolist()[:8] == ["Harbour Street"] * 4 + ["Mill Lane"] * 4
    assert out["Field"].tolist()[:8] == ["Jan", "Feb", "Mar", "Apr"] * 2


def test_leave_out_empty_values():
    res = run_block(HERE, [SAMPLE], {**FIXED, "drop_empty": True}).raise_for_error()
    out = res.output(0)
    assert len(out) == 21 and out["Value"].notna().all()
    assert ("Mill Lane", "Mar") not in set(zip(out["Store"], out["Field"]))
    assert "3 empty values left out" in res.final_message


def test_mixed_types_become_text():
    data = pd.DataFrame({"Id": ["A", "B"], "Count": [10, None], "Rate": [1.5, 2.0], "Note": ["x", "y"],
                         "When": pd.to_datetime(["2026-01-01", "2026-02-01"])})
    res = run_block(HERE, [data], {"fixed_fields": ["Id"]}).raise_for_error()
    out = res.output(0)
    values = out["Value"].tolist()
    assert values[:4] == ["10", "1.5", "x", "2026-01-01"]
    assert pd.isna(values[4]) and values[5:] == ["2", "y", "2026-02-01"]
    assert all(isinstance(v, str) for v in out["Value"].dropna())
    assert "turned into text" in res.final_message


def test_dates_with_times_keep_the_time_as_text():
    data = pd.DataFrame({"Id": [1], "At": pd.to_datetime(["2026-01-01 08:30:00"]), "Note": ["x"]})
    out = melt(data, fixed_fields=["Id"])
    assert out["Value"].tolist() == ["2026-01-01 08:30:00", "x"]


def test_same_type_fields_keep_their_type():
    data = pd.DataFrame({"Id": [1, 2], "Start": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                         "End": pd.to_datetime(["2026-02-01", "2026-02-02"])})
    out = melt(data, fixed_fields=["Id"])
    assert pd.api.types.is_datetime64_any_dtype(out["Value"])
    data = pd.DataFrame({"Id": [1], "A": [1], "B": [2.5]})
    out = melt(data, fixed_fields=["Id"])
    assert pd.api.types.is_float_dtype(out["Value"]) and out["Value"].tolist() == [1.0, 2.5]


def test_no_fixed_fields_de_pivots_everything():
    data = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    for unset in (None, [], ""):
        out = melt(data, fixed_fields=unset)
        assert list(out.columns) == ["Field", "Value"]
        assert out["Value"].tolist() == [1, 3, 2, 4]


def test_custom_names():
    out = melt(pd.DataFrame({"Id": [1], "A": [2]}), fixed_fields=["Id"], var_name="Month", value_name="Sales")
    assert list(out.columns) == ["Id", "Month", "Sales"]


def test_name_clashes_and_empty_names_abort():
    data = pd.DataFrame({"Store": ["A"], "Jan": [1]})
    for opts, text in [({"var_name": "Store"}, "already a fixed field"), ({"value_name": "Store"}, "already a fixed"),
                       ({"var_name": "X", "value_name": "X"}, "different names"), ({"var_name": " "}, "Give names")]:
        res = run_block(HERE, [data], {"fixed_fields": ["Store"], **opts})
        assert res.status == "aborted" and res.error is None, opts
        assert text in res.final_message


def test_unknown_fixed_field_and_no_input_abort():
    res = run_block(HERE, [pd.DataFrame({"A": [1]})], {"fixed_fields": ["B"]})
    assert res.status == "aborted" and "\"B\"" in res.final_message
    res = run_block(HERE, [], {})
    assert res.status == "aborted"


def test_all_fields_fixed_gives_no_records():
    out = melt(pd.DataFrame({"A": [1], "B": [2]}), fixed_fields=["A", "B"])
    assert len(out) == 0 and list(out.columns) == ["A", "B", "Field", "Value"]


def test_empty_input():
    data = pd.DataFrame({"Id": pd.Series([], dtype=object), "A": pd.Series([], dtype="Int64")})
    out = melt(data, fixed_fields=["Id"])
    assert len(out) == 0 and list(out.columns) == ["Id", "Field", "Value"]


def test_large_input():
    n = 100000
    data = pd.DataFrame({"Id": np.arange(n), **{f"M{i}": np.arange(n) * i for i in range(12)}})
    t = time.time()
    out = melt(data, fixed_fields=["Id"])
    elapsed = time.time() - t
    assert len(out) == 1200000
    assert out["Field"].tolist()[:13] == [f"M{i}" for i in range(12)] + ["M0"]
    assert out["Value"].iloc[12 * 7 + 5] == 7 * 5
    assert elapsed < 30
