import os
import time

import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "mailing-list.csv")


def test_sample_in_batches_of_ten():
    out = run_block(HERE, SAMPLE, {"partition_size": 10}).raise_for_error().output(0)
    assert len(out) == 23
    assert list(out.columns) == ["Contact", "Name", "Email", "Region", "Signed up", "Partition"]
    assert out["Partition"].value_counts().sort_index().to_dict() == {1: 10, 2: 10, 3: 3}
    assert out["Partition"].tolist() == [1] * 10 + [2] * 10 + [3] * 3
    assert out["Contact"].tolist() == [f"CT-{n}" for n in range(1001, 1024)]  # order kept


def test_partition_is_a_whole_number_that_sorts_correctly():
    out = run_block(HERE, pd.DataFrame({"a": range(25)}), {"partition_size": 2}).raise_for_error().output(0)
    assert pd.api.types.is_integer_dtype(out["Partition"])
    assert sorted(out["Partition"].unique())[-3:] == [11, 12, 13]  # as text, "10" and "11" sorted before "2"


def test_default_size_is_1000():
    out = run_block(HERE, pd.DataFrame({"a": range(2500)})).raise_for_error().output(0)
    assert out["Partition"].value_counts().sort_index().to_dict() == {1: 1000, 2: 1000, 3: 500}


def test_numbering_carries_on_across_stream_chunks():
    # the harness streams 10,000 records at a time, like Omniscope
    out = run_block(HERE, pd.DataFrame({"a": range(25000)}), {"partition_size": 3000}).raise_for_error().output(0)
    counts = out["Partition"].value_counts().sort_index().to_dict()
    assert counts == {**{p: 3000 for p in range(1, 9)}, 9: 1000}


def test_size_one_numbers_every_record():
    out = run_block(HERE, pd.DataFrame({"a": [5, 6, 7]}), {"partition_size": 1}).raise_for_error().output(0)
    assert out["Partition"].tolist() == [1, 2, 3]


def test_existing_partition_field_is_replaced():
    data = pd.DataFrame({"Partition": ["x", "y"], "a": [1, 2]})
    out = run_block(HERE, data, {"partition_size": 1}).raise_for_error().output(0)
    assert list(out.columns) == ["Partition", "a"]
    assert out["Partition"].tolist() == [1, 2]


def test_other_fields_keep_their_types():
    data = pd.DataFrame({"n": pd.array([1, None, 3], dtype="Int64"), "d": pd.to_datetime(["2026-01-01"] * 3)})
    out = run_block(HERE, data, {"partition_size": 2}).raise_for_error().output(0)
    assert str(out["n"].dtype) == "Int64" and pd.api.types.is_datetime64_any_dtype(out["d"])


def test_bad_size_aborts():
    for size in (0, -5, None):
        res = run_block(HERE, pd.DataFrame({"a": [1]}), {"partition_size": size})
        assert res.status == "aborted" and res.error is None, size
        assert "1 or more" in res.final_message


def test_empty_input():
    out = run_block(HERE, pd.DataFrame({"a": pd.Series([], dtype="Int64")}), {"partition_size": 5})
    out = out.raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["a", "Partition"]


def test_large_input():
    data = pd.DataFrame({"a": range(500000)})
    t = time.time()
    out = run_block(HERE, data, {"partition_size": 1000}).raise_for_error().output(0)
    elapsed = time.time() - t
    assert out["Partition"].iloc[-1] == 500 and out["Partition"].iloc[999] == 1 and out["Partition"].iloc[1000] == 2
    assert elapsed < 5
