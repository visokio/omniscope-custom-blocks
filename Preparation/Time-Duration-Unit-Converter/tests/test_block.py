import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "support-calls.csv")
BOTH = {"date_fields": ["Started", "Handling time"], "unit": "m"}


def by_call(df, field):
    return dict(zip(df["Call"], df[field]))


def test_sample_calls_in_minutes():
    res = run_block(HERE, SAMPLE, BOTH).raise_for_error()
    out = res.output(0)
    assert len(out) == 12
    assert list(out.columns) == ["Call", "Agent", "Started", "Handling time", "Started_m", "Handling time_m"]
    assert out["Started_m"].dtype == "float64" and out["Handling time_m"].dtype == "float64"
    started, handling = by_call(out, "Started_m"), by_call(out, "Handling time_m")
    assert started["C-0401"] == pytest.approx(8 * 60 + 31.25)      # 08:31:15, date ignored
    assert started["C-0411"] == 8 * 60 + 5                          # another day, same rule
    assert handling["C-0401"] == pytest.approx(4 + 35 / 60)         # 0:04:35
    assert handling["C-0402"] == 12                                 # 12 min
    assert handling["C-0403"] == 65                                 # 1h 5m
    assert handling["C-0405"] == 6.5                                # 0:06:30
    assert handling["C-0407"] == 18                                 # PT18M
    assert handling["C-0409"] == 0.75                               # 45 s
    assert handling["C-0412"] == 120                                # 2h
    assert np.isnan(handling["C-0406"])                             # missing stays missing
    assert np.isnan(handling["C-0411"])                             # "about 10 min" can't be read
    assert out["Handling time_m"].notna().sum() == 10
    assert res.messages == ["Not read as a time or duration (left empty): 1 in Handling time"]


@pytest.mark.parametrize("unit,expected", [("ms", 275_000), ("s", 275), ("m", 275 / 60), ("h", 275 / 3600)])
def test_each_unit(unit, expected):
    out = run_block(HERE, SAMPLE, {"date_fields": ["Handling time"], "unit": unit}).raise_for_error().output(0)
    assert by_call(out, f"Handling time_{unit}")["C-0401"] == pytest.approx(expected)


def test_missing_dates_stay_missing():
    # The original script stopped with "cannot convert float NaN to integer" on an empty date
    df = pd.DataFrame({"d": pd.to_datetime(["2025-01-01 08:30", None, "2025-01-02 00:00"])})
    out = run_block(HERE, df, {"date_fields": ["d"], "unit": "h"}).raise_for_error().output(0)
    assert out["d_h"].iloc[0] == 8.5 and np.isnan(out["d_h"].iloc[1]) and out["d_h"].iloc[2] == 0


def test_hours_and_minutes_text():
    # The original left "08:30" empty: pandas reads hh:mm:ss but not hh:mm
    df = pd.DataFrame({"t": ["08:30", "8:30", "17:05", "-0:30", "08:30:00"]})
    out = run_block(HERE, df, {"date_fields": ["t"], "unit": "m"}).raise_for_error().output(0)
    assert out["t_m"].tolist() == [510, 510, 1025, -30, 510]


def test_other_duration_texts():
    df = pd.DataFrame({"t": ["1 day 02:00:00", "90 min", "1:45:20.5", " 2 hours ", "PT1H30M", "n/a text", "3"]})
    out = run_block(HERE, df, {"date_fields": ["t"], "unit": "s"}).raise_for_error().output(0)
    got = out["t_s"].tolist()
    assert got[:5] == [93600, 5400, 6320.5, 7200, 5400]
    assert np.isnan(got[5]) and np.isnan(got[6])  # no unit: the original read "3" as 3 nanoseconds


def test_empty_input_gives_number_fields():
    # The original's new field took the input's type when there were no records (a Date field, not a number)
    df = pd.DataFrame({"d": pd.Series([], dtype="datetime64[ns]"), "t": pd.Series([], dtype=object)})
    out = run_block(HERE, df, {"date_fields": ["d", "t"], "unit": "s"}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["d", "t", "d_s", "t_s"]
    assert out["d_s"].dtype == "float64" and out["t_s"].dtype == "float64"


def test_bad_choices_abort_with_a_message():
    df = pd.DataFrame({"n": [1, 2], "t": ["0:01:00", "0:02:00"]})
    res = run_block(HERE, df, {"date_fields": ["n"]})
    assert res.status == "aborted" and "number field" in res.final_message
    res = run_block(HERE, df, {"date_fields": None})
    assert res.status == "aborted" and "Choose" in res.final_message
    # The original skipped a missing field without a word
    res = run_block(HERE, df, {"date_fields": ["gone"]})
    assert res.status == "aborted" and "not in the input" in res.final_message
    res = run_block(HERE, None, {"date_fields": ["t"]})
    assert res.status == "aborted" and "Connect" in res.final_message


def test_unit_default_is_seconds():
    out = run_block(HERE, SAMPLE, {"date_fields": ["Handling time"]}).raise_for_error().output(0)
    assert "Handling time_s" in out.columns


def test_large_input_is_fast():
    n = 200_000
    rng = np.random.default_rng(0)
    secs = rng.integers(0, 86_400, n)
    df = pd.DataFrame({
        "when": pd.Timestamp("2025-01-01") + pd.to_timedelta(secs, unit="s"),
        "dur": [f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" for s in secs],
    })
    t0 = time.time()
    out = run_block(HERE, df, {"date_fields": ["when", "dur"], "unit": "s"}).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert (out["when_s"].to_numpy() == secs).all() and (out["dur_s"].to_numpy() == secs).all()
