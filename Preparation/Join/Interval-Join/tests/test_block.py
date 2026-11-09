import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
PARCELS = os.path.join(HERE, "sample-data", "parcels.csv")
TARIFF = os.path.join(HERE, "sample-data", "tariff.csv")
SAMPLE_OPTIONS = {"value": "Weight kg", "start": "From kg", "end": "To kg", "left": "Zone", "right": "Zone"}


def run(first, second, **options):
    return run_block(HERE, [first, second], options)


def join(first, second, **options):
    return run(first, second, **options).raise_for_error().output(0)


def test_sample_inner_join_by_zone():
    res = run(PARCELS, TARIFF, **SAMPLE_OPTIONS).raise_for_error()
    out = res.output(0)
    assert list(out.columns) == ["Parcel", "Zone", "Weight kg", "Sent", "Zone.1", "From kg", "To kg", "Band", "Price"]
    assert dict(zip(out["Parcel"], out["Band"])) == {
        "P-101": "Small", "P-102": "Medium", "P-103": "Large", "P-104": "Small", "P-105": "Medium",
        "P-106": "Large", "P-107": "Heavy", "P-108": "Standard", "P-112": "Heavy"}
    assert res.final_message == "9 of 12 records in an interval; 9 records out"


def test_sample_left_join_keeps_every_parcel():
    out = join(PARCELS, TARIFF, join_type="LEFT", **SAMPLE_OPTIONS)
    assert len(out) == 12
    assert list(out["Parcel"]) == [f"P-{n}" for n in range(101, 113)]
    unmatched = out[out["Band"].isna()]["Parcel"].tolist()
    assert unmatched == ["P-109", "P-110", "P-111"]  # too heavy for Islands, no Overseas tariff, no weight


def test_dates_and_whole_numbers_keep_their_types():
    out = join(PARCELS, TARIFF, join_type="LEFT", **SAMPLE_OPTIONS)
    assert pd.api.types.is_datetime64_any_dtype(out["Sent"])
    assert str(out["From kg"].dtype) == "Int64"


def test_date_intervals():
    orders = pd.DataFrame({"Order": [1, 2, 3, 4], "Date": pd.to_datetime(
        ["2026-01-05", "2026-02-01", "2026-02-01 12:30", "2026-03-31"], format="mixed")})
    prices = pd.DataFrame({"From": pd.to_datetime(["2026-01-01", "2026-02-01"]),
                           "To": pd.to_datetime(["2026-02-01", "2026-03-01"]), "Price": [1.5, 2.5]})
    out = join(orders, prices, value="Date", start="From", end="To", join_type="LEFT")
    assert out["Price"].tolist()[:3] == [1.5, 2.5, 2.5] and pd.isna(out["Price"][3])
    assert pd.api.types.is_datetime64_any_dtype(out["Date"]) and pd.api.types.is_datetime64_any_dtype(out["To"])


def test_inclusive_and_exclusive_ends():
    left = pd.DataFrame({"v": [5, 7, 10]})
    right = pd.DataFrame({"s": [5], "e": [10]})
    cases = {(">=", "<"): [5, 7], (">=", "<="): [5, 7, 10], (">", "<"): [7], (">", "<="): [7, 10]}
    for (sc, ec), expected in cases.items():
        out = join(left, right, value="v", start="s", end="e", start_comparator=sc, end_comparator=ec)
        assert out["v"].tolist() == expected, (sc, ec)


def test_empty_start_or_end_is_open():
    left = pd.DataFrame({"v": [-100, 5, 1000]})
    right = pd.DataFrame({"s": [None, 0, 10], "e": [0, 10, None], "band": ["below", "mid", "above"]})
    out = join(left, right, value="v", start="s", end="e")
    assert out["band"].tolist() == ["below", "mid", "above"]


def test_overlapping_intervals_give_one_record_each_in_input_order():
    left = pd.DataFrame({"v": [3, 1]})
    right = pd.DataFrame({"s": [2, 0, 0], "e": [4, 5, 2], "name": ["b", "a", "c"]})
    out = join(left, right, value="v", start="s", end="e")
    assert list(zip(out["v"], out["name"])) == [(3, "b"), (3, "a"), (1, "a"), (1, "c")]


def test_interval_that_ends_before_it_starts_is_ignored():
    res = run(pd.DataFrame({"v": [5]}), pd.DataFrame({"s": [10, 0], "e": [0, 10]}), value="v", start="s", end="e")
    assert len(res.raise_for_error().output(0)) == 1
    assert "1 intervals end before they start" in res.final_message


def test_equality_field_must_be_chosen_on_both_sides():
    res = run(pd.DataFrame({"v": [1], "k": ["a"]}), pd.DataFrame({"s": [0], "e": [5], "k2": ["b"]}),
              value="v", start="s", end="e", left="k")
    assert res.status == "aborted" and "both inputs" in res.final_message


def test_equality_field_with_missing_keys():
    left = pd.DataFrame({"v": [1, 1], "k": ["a", None]})
    right = pd.DataFrame({"s": [0, 0], "e": [5, 5], "k": ["a", None]})
    out = join(left, right, value="v", start="s", end="e", left="k", right="k", join_type="LEFT")
    assert out["k.1"].tolist()[0] == "a" and pd.isna(out["k.1"][1])  # missing keys match nothing


def test_text_and_mixed_types_abort():
    res = run(pd.DataFrame({"v": ["9", "10"]}), pd.DataFrame({"s": ["1"], "e": ["5"]}), value="v", start="s", end="e")
    assert res.status == "aborted" and "numbers or dates" in res.final_message
    prices = pd.DataFrame({"From": pd.to_datetime(["2026-01-01"]), "To": pd.to_datetime(["2026-02-01"])})
    res = run(pd.DataFrame({"v": [5]}), prices, value="v", start="From", end="To")
    assert res.status == "aborted" and "all numbers or all dates" in res.final_message


def test_missing_inputs_and_fields_abort():
    res = run_block(HERE, [pd.DataFrame({"v": [1]})], {"value": "v", "start": "s", "end": "e"})
    assert res.status == "aborted" and "second input" in res.final_message
    res = run(pd.DataFrame({"v": [1]}), pd.DataFrame({"s": [0], "e": [5]}), value="v", start="x", end="e")
    assert res.status == "aborted" and "\"x\"" in res.final_message
    res = run(pd.DataFrame({"v": [1]}), pd.DataFrame({"s": [0], "e": [5]}), start="s", end="e")
    assert res.status == "aborted" and "Value in interval" in res.final_message


def test_clashing_field_names_get_a_suffix():
    out = join(pd.DataFrame({"v": [1], "Name": ["x"]}), pd.DataFrame({"v": [0], "e": [5], "Name": ["y"]}),
               value="v", start="v", end="e")
    assert list(out.columns) == ["v", "Name", "v.1", "e", "Name.1"]


def test_field_names_with_spaces_and_sql_words():
    out = join(pd.DataFrame({"order": [1], "my value": [2]}), pd.DataFrame({"from": [0], "to at": [5]}),
               value="my value", start="from", end="to at")
    assert len(out) == 1


def test_empty_inputs():
    left = pd.DataFrame({"v": pd.Series([], dtype="Int64"), "t": pd.Series([], dtype=object)})
    right = pd.DataFrame({"s": [0], "e": [5], "x": ["a"]})
    for jt in ("INNER", "LEFT"):
        out = join(left, right, value="v", start="s", end="e", join_type=jt)
        assert len(out) == 0 and list(out.columns) == ["v", "t", "s", "e", "x"]
    out = join(pd.DataFrame({"v": [1, 2]}), right.iloc[0:0], value="v", start="s", end="e", join_type="LEFT")
    assert len(out) == 2 and out["x"].isna().all()


def test_large_input():
    rng = np.random.default_rng(0)
    n = 200000
    left = pd.DataFrame({"id": np.arange(n), "v": rng.uniform(0, 10000, n)})
    bounds = np.arange(0, 10001, 10)
    right = pd.DataFrame({"s": bounds[:-1], "e": bounds[1:], "band": np.arange(len(bounds) - 1)})
    t = time.time()
    out = join(left, right, value="v", start="s", end="e")
    elapsed = time.time() - t
    assert len(out) == n
    assert (out["band"] == (out["v"] // 10).astype(int)).all()
    assert elapsed < 30
