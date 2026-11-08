import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "customer-exports.csv")
DEMO = {"day_first": True, "auto_cast_threshold": 0.9}


def run(df, **options):
    return run_block(HERE, df, options).raise_for_error().output(0)


def test_sample_exports():
    out = run(SAMPLE, **DEMO)
    assert len(out) == 12
    assert list(out.columns) == ["customer_id", "name", "sign_up_date", "monthly_spend", "orders", "active", "region"]
    # the two ID fields and the two spend fields are merged
    assert out["customer_id"].tolist() == [f"C-{i:03d}" for i in range(1, 13)]
    assert out["monthly_spend"].tolist()[:4] == [120.5, 89.0, 240.0, 56.25]
    assert pd.isna(out["monthly_spend"].iloc[8])          # missing in both: stays missing, not 0
    # mixed date formats, day first; ISO dates stay year-month-day
    assert pd.api.types.is_datetime64_any_dtype(out["sign_up_date"])
    assert out["sign_up_date"].iloc[2] == pd.Timestamp("2024-03-02")
    assert out["sign_up_date"].iloc[3] == pd.Timestamp("2024-03-04")
    assert pd.isna(out["sign_up_date"].iloc[7])
    # 11 of 12 orders are numbers: above the 0.9 threshold, so Integer, and "unknown" becomes missing
    assert str(out["orders"].dtype) == "Int64" and pd.isna(out["orders"].iloc[3]) and out["orders"].sum() == 139
    # yes / no / Y / N, with one missing
    assert out["active"].tolist()[:4] == [True, False, True, False] and pd.isna(out["active"].iloc[7])


def test_default_threshold_keeps_a_field_with_junk_as_text():
    out = run(SAMPLE)
    assert out["orders"].tolist()[3] == "unknown"           # 11 of 12 is below 0.98


def test_missing_values_do_not_block_the_cast():
    # The original counted missing values against the threshold: a number field with one gap came out as text
    df = pd.DataFrame({"n": ["1.5", None, "2.5", "3"], "flag": ["yes", "no", None, "y"]}, dtype=object)
    out = run(df)
    assert pd.api.types.is_float_dtype(out["n"]) and out["n"].tolist()[0] == 1.5 and pd.isna(out["n"].iloc[1])
    assert str(out["flag"].dtype) == "boolean" and pd.isna(out["flag"].iloc[2])


def test_missing_values_stay_missing_unless_a_default_is_set():
    # The original filled missing numbers with 0, dates with 1970-01-01 and text with ""
    df = pd.DataFrame({"n": [1.0, None, 3.0], "t": ["a", None, "c"],
                       "d": pd.to_datetime(["2025-01-01", None, "2025-01-03"])})
    out = run(df)
    assert pd.isna(out["n"].iloc[1]) and pd.isna(out["t"].iloc[1]) and pd.isna(out["d"].iloc[1])
    out = run(df, number_default="0", string_default="n/a", datetime_default="2000-01-01")
    assert out["n"].iloc[1] == 0 and out["t"].iloc[1] == "n/a"
    assert out["d"].iloc[1].tz_localize(None) == pd.Timestamp("2000-01-01")


def test_date_and_number_fields_keep_their_type():
    # The original turned a Date field into a number (microseconds since 1970)
    df = pd.DataFrame({"Order Date": pd.to_datetime(["2025-01-01", "2025-02-01"]), "Qty": [3, 4]})
    out = run(df)
    assert pd.api.types.is_datetime64_any_dtype(out["order_date"])
    assert out["qty"].tolist() == [3, 4]


def test_leading_zeros_stay_text():
    df = pd.DataFrame({"code": ["00123", "00456", "01789"], "amount": ["0.5", "10", "-0.25"]}, dtype=object)
    out = run(df)
    assert out["code"].tolist() == ["00123", "00456", "01789"]
    assert out["amount"].tolist() == [0.5, 10.0, -0.25]


def test_words_are_not_dates():
    # pandas reads "March" as 1 March in year 1
    df = pd.DataFrame({"m": ["March", "April", "May"], "d": ["2025-01-02", "2025-02-03", "2025-03-04 10:00"]},
                      dtype=object)
    out = run(df)
    assert out["m"].tolist() == ["March", "April", "May"]
    assert out["d"].dt.tz_localize(None).tolist()[2] == pd.Timestamp("2025-03-04 10:00")  # arrives as a Date field


def test_names_and_coalescing():
    df = pd.DataFrame({"First Name": ["Ann", None, ""], "first-name": ["X", "Bob", "Cy"], "first_name": [None, "Z", None]},
                      dtype=object)
    out = run(df)
    assert list(out.columns) == ["first_name"] and out["first_name"].tolist() == ["Ann", "Bob", "Cy"]
    out = run(df, prefer_non_empty_strings=False)
    assert out["first_name"].tolist()[:2] == ["Ann", "Bob"]


def test_sort_columns():
    df = pd.DataFrame({"Zeta": ["a"], "alpha": ["b"], "Mid Name": ["c"]})
    assert list(run(df).columns) == ["zeta", "alpha", "mid_name"]
    assert list(run(df, sort_columns=True).columns) == ["alpha", "mid_name", "zeta"]


def test_empty_input():
    df = pd.DataFrame({"A Field": pd.Series([], dtype=object), "n": pd.Series([], dtype="int64")})
    out = run(df)
    assert len(out) == 0 and list(out.columns) == ["a_field", "n"]


def test_bad_options_abort():
    df = pd.DataFrame({"a": ["x"]})
    res = run_block(HERE, df, {"auto_cast_threshold": 1.5})
    assert res.status == "aborted" and "threshold" in res.final_message
    res = run_block(HERE, df, {"datetime_default": "not a date"})
    assert res.status == "aborted" and "Datetime default" in res.final_message
    res = run_block(HERE, df, {"number_default": "lots"})
    assert res.status == "aborted" and "Number default" in res.final_message


def test_large_input():
    n = 200_000
    rng = np.random.default_rng(0)
    df = pd.DataFrame({
        "Order ID": [f"O-{i}" for i in range(n)],
        "Amount": rng.normal(100, 20, n).round(2).astype(str),
        "Order-Date": (pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D"))
        .strftime("%Y-%m-%d").astype(object),
        "Paid": rng.choice(["yes", "no"], n),
    }, dtype=object)
    df.loc[::1000, "Order-Date"] = "15/03/2024"  # mixed formats
    t0 = time.time()
    out = run(df)
    assert time.time() - t0 < 60
    assert pd.api.types.is_float_dtype(out["amount"]) and pd.api.types.is_datetime64_any_dtype(out["order_date"])
    assert str(out["paid"].dtype) == "boolean" and out["paid"].notna().all() and len(out) == n


def test_types_are_decided_by_the_first_chunk_and_kept():
    # The original chose types chunk by chunk, so a field could be a number in one chunk and text in the next,
    # which Omniscope rejects. Now the first chunk (10,000 records in the stand-in) decides, later values that
    # don't fit become missing, and the block's message counts them.
    n = 25_000
    count = [str(i % 50) for i in range(n)]
    when = ["2024-03-%02d" % (1 + i % 28) for i in range(n)]
    flag = (["yes", "no"] * n)[:n]
    late = [None] * n
    count[12_345], count[20_001] = "2.5", "lots"           # a fraction in an Integer field, and a word
    when[15_000] = "soon"
    flag[24_999] = "maybe"
    for i in range(10_000, n):
        late[i] = str(i)                                    # empty in the first chunk: stays text
    df = pd.DataFrame({"Count": count, "When": when, "Flag": flag, "Late": late}, dtype=object)
    res = run_block(HERE, df, {}).raise_for_error()
    out = res.output(0)
    assert len(out) == n and list(out.columns) == ["count", "when", "flag", "late"]
    assert str(out["count"].dtype) == "Int64" and out["count"].isna().sum() == 2 and pd.isna(out["count"].iloc[12_345])
    assert pd.api.types.is_datetime64_any_dtype(out["when"]) and out["when"].isna().sum() == 1
    assert str(out["flag"].dtype) == "boolean" and out["flag"].isna().sum() == 1
    assert out["late"].iloc[-1] == str(n - 1)
    assert res.final_message == "Values that didn't fit their field's type (now empty): count 2, when 1, flag 1"


def test_a_decimal_first_chunk_keeps_later_whole_numbers_as_decimals():
    n = 15_000
    df = pd.DataFrame({"Price": ["1.5"] * 10_000 + ["2"] * (n - 10_000)}, dtype=object)
    res = run_block(HERE, df, {}).raise_for_error()
    out = res.output(0)
    assert out["price"].dtype == "float64" and out["price"].iloc[-1] == 2.0 and res.final_message == ""
