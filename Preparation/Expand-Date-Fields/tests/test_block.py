import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block
from omniscope import api as fake_api

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "orders.csv")
BOTH = {"dateFields": ["Order Date", "Delivery Date"]}
PARTS = ["year", "month", "month_name", "day", "day_name", "dayofyear", "quarter",
         "is_month_start", "is_month_end", "weekofyear", "week_year"]


def run_raw(monkeypatch, df, options):
    """Run without the stand-in's Omniscope type conversion, so the script sees the values as given."""
    monkeypatch.setattr(fake_api, "omniscope_dtypes", lambda frame: frame)
    return run_block(HERE, df, options)


def row(out, order):
    return out[out["Order"] == order].iloc[0]


def test_sample_orders_get_date_parts_for_both_fields():
    out = run_block(HERE, SAMPLE, BOTH).raise_for_error().output(0)
    assert len(out) == 16
    original = ["Order", "Customer", "Order Date", "Delivery Date", "Value"]
    assert list(out.columns) == original + [f"Order Date_{p}" for p in PARTS] + [f"Delivery Date_{p}" for p in PARTS]
    r = row(out, "WO-3008")  # ordered Friday 30 January 2026, delivered Saturday 31 January
    assert (r["Order Date_year"], r["Order Date_month"], r["Order Date_day"]) == (2026, 1, 30)
    assert r["Order Date_month_name"] == "January" and r["Order Date_day_name"] == "Friday"
    assert r["Order Date_quarter"] == 1 and r["Order Date_dayofyear"] == 30
    assert r["Delivery Date_day_name"] == "Saturday" and r["Delivery Date_is_month_end"] == True  # noqa: E712
    assert r["Delivery Date_is_month_start"] == False  # noqa: E712
    assert row(out, "WO-3009")["Order Date_quarter"] == 1
    assert row(out, "WO-3016")["Delivery Date_quarter"] == 2
    # the original fields keep their type
    assert pd.api.types.is_datetime64_any_dtype(out["Order Date"])
    assert str(out["Order Date_year"].dtype) == "Int64"


def test_iso_week_comes_with_its_own_year():
    # Monday 29 December 2025 is in ISO week 1 of 2026: grouping by calendar year and week would put it
    # with the first days of January 2025. The original block had no ISO year to group by.
    out = run_block(HERE, SAMPLE, {"dateFields": ["Order Date"]}).raise_for_error().output(0)
    r = row(out, "WO-3002")
    assert (r["Order Date_year"], r["Order Date_weekofyear"], r["Order Date_week_year"]) == (2025, 1, 2026)
    r = row(out, "WO-3001")
    assert (r["Order Date_weekofyear"], r["Order Date_week_year"]) == (52, 2025)


def test_missing_date_gives_empty_parts_not_false_flags():
    # The original block set the month start / end flags to False for a missing date
    out = run_block(HERE, SAMPLE, BOTH).raise_for_error().output(0)
    r = row(out, "WO-3015")
    for p in PARTS:
        assert pd.isna(r[f"Delivery Date_{p}"]), p
    assert row(out, "WO-3015")["Order Date_day_name"] == "Tuesday"


def test_time_of_day_does_not_shift_the_date():
    df = pd.DataFrame({"t": pd.to_datetime(["2026-03-31 23:59:59", "2026-04-01 00:00:00"])})
    out = run_block(HERE, df, {"dateFields": ["t"]}).raise_for_error().output(0)
    assert out["t_month"].tolist() == [3, 4]
    assert out["t_is_month_end"].tolist() == [True, False]
    assert out["t_is_month_start"].tolist() == [False, True]


def test_timezone_choices_on_dates_as_omniscope_sends_them():
    # Omniscope hands Date fields to the script in UTC, so the three choices give the same result
    outs = [run_block(HERE, SAMPLE, {"dateFields": ["Order Date"], "timezoneHandling": h}).raise_for_error().output(0)
            for h in ("PRESERVE_LOCAL", "CONVERT_TO_UTC", "REJECT_MIXED")]
    for o in outs[1:]:
        pd.testing.assert_frame_equal(outs[0], o)


def test_timezone_choices_on_dates_in_other_zones(monkeypatch):
    # Without the Omniscope dtype conversion the script sees the zones as given
    times = pd.Series([pd.Timestamp("2026-01-31 23:30", tz="Europe/London"),
                       pd.Timestamp("2026-02-01 00:30", tz="Europe/Paris")], dtype=object)
    df = pd.DataFrame({"t": times})
    local = run_raw(monkeypatch, df, {"dateFields": ["t"], "timezoneHandling": "PRESERVE_LOCAL"})
    assert local.raise_for_error().output(0)["t_day"].tolist() == [31, 1]
    utc = run_raw(monkeypatch, df, {"dateFields": ["t"], "timezoneHandling": "CONVERT_TO_UTC"})
    assert utc.raise_for_error().output(0)["t_day"].tolist() == [31, 31]
    mixed = run_raw(monkeypatch, df, {"dateFields": ["t"], "timezoneHandling": "REJECT_MIXED"})
    assert mixed.status == "aborted" and "Mixed" in mixed.final_message


def test_empty_input_keeps_the_fields():
    # The original block output a dataset with no fields at all
    df = pd.DataFrame({"id": pd.Series([], dtype="int64"), "d": pd.Series([], dtype="datetime64[ns]")})
    out = run_block(HERE, df, {"dateFields": ["d"]}).raise_for_error().output(0)
    assert len(out) == 0
    assert list(out.columns) == ["id", "d"] + [f"d_{p}" for p in PARTS]


def test_field_with_no_dates_still_gets_its_parts():
    # The original block left out the parts of a field with no valid dates (so the output fields changed
    # with the data), and aborted when no chosen field had any
    df = pd.DataFrame({"id": [1, 2], "a": pd.to_datetime(["2026-01-05", "2026-02-06"]),
                       "b": pd.Series([pd.NaT, pd.NaT], dtype="datetime64[ns]")})
    res = run_block(HERE, df, {"dateFields": ["a", "b"]}).raise_for_error()
    out = res.output(0)
    assert [f"b_{p}" for p in PARTS] == [c for c in out.columns if c.startswith("b_")]
    assert out["b_year"].isna().all() and out["a_year"].tolist() == [2026, 2026]
    assert "b" in res.final_message
    res = run_block(HERE, df, {"dateFields": ["b"]}).raise_for_error()
    assert res.output(0)["b_month"].isna().all()


def test_wrong_types_and_bad_options(monkeypatch):
    df = pd.DataFrame({"n": [20260105, 3], "d": pd.to_datetime(["2026-01-05", "2026-02-06"])})
    # a number is not read as nanoseconds since 1970
    res = run_block(HERE, df, {"dateFields": ["n"]})
    assert res.status == "aborted" and "n" in res.final_message and "date" in res.final_message.lower()
    res = run_block(HERE, df, {"dateFields": None})
    assert res.status == "aborted" and "Choose" in res.final_message
    res = run_block(HERE, df, {"dateFields": ["missing"]})
    assert res.status == "aborted" and "missing" in res.final_message
    assert run_block(HERE, None, {"dateFields": ["d"]}).status == "aborted"
    # text holding dates is read as dates
    txt = pd.DataFrame({"s": ["5 January 2026", "not a date", None]})
    out = run_raw(monkeypatch, txt, {"dateFields": ["s"]}).raise_for_error().output(0)
    assert out["s_day_name"].tolist()[0] == "Monday" and out["s_year"].isna().tolist() == [False, True, True]


def test_large_input_is_fast():
    n = 1_000_000
    rng = np.random.default_rng(0)
    d = pd.Timestamp("2020-01-01") + pd.to_timedelta(rng.integers(0, 6 * 365 * 24 * 3600, n), unit="s")
    df = pd.DataFrame({"id": np.arange(n), "d": d})
    t0 = time.time()
    out = run_block(HERE, df, {"dateFields": ["d"]}).raise_for_error().output(0)
    assert time.time() - t0 < 60
    assert len(out) == n and out["d_year"].between(2020, 2026).all()
