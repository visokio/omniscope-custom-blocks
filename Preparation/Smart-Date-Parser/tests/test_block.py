import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "supplier-deliveries.csv")
DEMO = {"fields_to_parse": ["Order Date", "Delivered At"], "prefer_day_first": True, "custom_formats": "%y%m%d"}


def ts(s):
    return pd.Timestamp(s)


def run(df, **options):
    return run_block(HERE, df, options).raise_for_error().output(0)


def test_sample_deliveries():
    out = run(SAMPLE, **DEMO)
    assert len(out) == 12
    assert list(out.columns) == ["Delivery", "Supplier",
                                 "Order Date", "Order Date_parsed", "Order Date_parsed_failed",
                                 "Delivered At", "Delivered At_parsed", "Delivered At_parsed_failed"]
    assert pd.api.types.is_datetime64_any_dtype(out["Order Date_parsed"])
    order = dict(zip(out["Delivery"], out["Order Date_parsed"]))
    assert order["D-101"] == ts("2025-03-04")      # ISO stays year-month-day with Day first ticked
    assert order["D-103"] == ts("2025-03-04")      # 04/03/2025, day first
    assert order["D-105"] == ts("2025-03-05")      # 5 March 2025
    assert order["D-106"] == ts("2025-03-12")      # March 12, 2025
    assert order["D-107"] == ts("2025-03-07")      # 250307 through the custom format %y%m%d
    assert order["D-109"] == ts("2025-03-19")      # 20250319
    failed = out.loc[out["Order Date_parsed_failed"], "Delivery"].tolist()
    assert failed == ["D-111", "D-112"]            # "March 2025" and "31/02/2025"
    delivered = dict(zip(out["Delivery"], out["Delivered At_parsed"]))
    assert delivered["D-101"] == ts("2025-03-06 09:30")
    assert delivered["D-103"] == ts("2025-03-06 11:20")
    assert delivered["D-107"] == ts("2025-03-10 07:50")  # +01:00 converted to UTC
    assert pd.isna(delivered["D-110"])
    assert not out["Delivered At_parsed_failed"].any()  # a missing value is not a failure
    assert out["Delivered At_parsed"].notna().sum() == 11


def test_iso_dates_are_not_swapped_with_day_first():
    # The original read 2025-03-04 as 3 April when Day first was ticked
    df = pd.DataFrame({"d": ["2025-03-04", "2025-03-11T10:00:00+01:00", "2025/03/04"]})
    out = run(df, fields_to_parse=["d"], prefer_day_first=True)
    assert out["d_parsed"].tolist() == [ts("2025-03-04"), ts("2025-03-11 09:00"), ts("2025-03-04")]


def test_month_first_when_day_first_unticked():
    df = pd.DataFrame({"d": ["04/03/2025", "13/03/2025"]})
    out = run(df, fields_to_parse=["d"])
    assert out["d_parsed"].tolist() == [ts("2025-04-03"), ts("2025-03-13")]  # 13 can only be a day


def test_mixed_time_zones_are_all_parsed():
    # The original lost every value when a field mixed values with and without a time zone
    df = pd.DataFrame({"d": ["2025-03-06T09:30:00Z", "06/03/2025 11:20", "2025-03-10T08:50:00+01:00"]})
    out = run(df, fields_to_parse=["d"], prefer_day_first=True)
    assert out["d_parsed"].tolist() == [ts("2025-03-06 09:30"), ts("2025-03-06 11:20"), ts("2025-03-10 07:50")]
    assert not out["d_parsed_failed"].any()


def test_incomplete_dates_fail_instead_of_borrowing_today():
    # The original filled missing parts from the day it ran: "12" became the 12th of the current month
    df = pd.DataFrame({"d": ["12", "2025", "March", "March 2025", "Q3 2025", "1 March 2025"]})
    out = run(df, fields_to_parse=["d"])
    assert out["d_parsed_failed"].tolist() == [True, True, True, True, True, False]
    assert out["d_parsed"].iloc[5] == ts("2025-03-01")


def test_custom_formats_are_tried_first():
    # dateutil reads 250307 as 25 March 2007; the original tried custom formats only after it
    df = pd.DataFrame({"d": ["250307", "03.04.2025"]})
    out = run(df, fields_to_parse=["d"], custom_formats="%y%m%d, %d.%m.%Y")
    assert out["d_parsed"].tolist() == [ts("2025-03-07"), ts("2025-04-03")]


def test_defaults_add_a_flag_and_keep_the_original():
    # The manifest left these options unset (unticked), which contradicted the documented defaults
    out = run(pd.DataFrame({"d": ["2025-01-02", "nonsense"]}), fields_to_parse=["d"])
    assert list(out.columns) == ["d", "d_parsed", "d_parsed_failed"]
    assert out["d_parsed_failed"].tolist() == [False, True]


def test_in_place_and_dropping_originals():
    df = pd.DataFrame({"id": [1, 2], "d": ["2025-01-02", "bad"]})
    out = run(df, fields_to_parse=["d"], output_suffix="", add_failure_flag=False)
    assert list(out.columns) == ["id", "d"] and out["d"].iloc[0] == ts("2025-01-02") and pd.isna(out["d"].iloc[1])
    out = run(df, fields_to_parse=["d"], output_suffix=" (date)", keep_original_fields=False)
    assert list(out.columns) == ["id", "d (date)", "d (date)_failed"]


def test_numbers_and_date_fields():
    df = pd.DataFrame({"n": [20250319, None, 20250320], "d": pd.to_datetime(["2025-01-01", None, "2025-01-03"])})
    out = run(df, fields_to_parse=["n", "d"])
    assert out["n_parsed"].tolist()[0] == ts("2025-03-19") and pd.isna(out["n_parsed"].iloc[1])
    assert out["d_parsed"].notna().sum() == 2 and not out["d_parsed_failed"].any()


def test_empty_input():
    df = pd.DataFrame({"id": pd.Series([], dtype="int64"), "d": pd.Series([], dtype=object)})
    out = run(df, fields_to_parse=["d"])
    assert len(out) == 0 and list(out.columns) == ["id", "d", "d_parsed", "d_parsed_failed"]


def test_bad_options_abort():
    df = pd.DataFrame({"d": ["2025-01-01"], "d_parsed": ["x"]})
    res = run_block(HERE, df, {"fields_to_parse": None})
    assert res.status == "aborted" and "Choose" in res.final_message
    res = run_block(HERE, df, {"fields_to_parse": ["d"]})
    assert res.status == "aborted" and "d_parsed" in res.final_message


def test_large_input():
    n = 100_000
    rng = np.random.default_rng(0)
    days = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 730, n), unit="D")
    styles = rng.integers(0, 3, n)
    text = [d.strftime(["%Y-%m-%d", "%d/%m/%Y", "%d %b %Y"][s]) for d, s in zip(days, styles)]
    t0 = time.time()
    out = run(pd.DataFrame({"d": text}), fields_to_parse=["d"], prefer_day_first=True)
    assert time.time() - t0 < 60
    assert (out["d_parsed"] == pd.Series(days.as_unit("us"))).all()
