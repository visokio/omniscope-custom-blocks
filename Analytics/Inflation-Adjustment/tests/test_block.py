import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAL = os.path.join(HERE, "sample-data", "salaries.csv")
IDX = os.path.join(HERE, "sample-data", "price-index.csv")
O = {"date_field": "d", "value_fields": ["v"], "index_date_field": "m", "index_value_field": "i"}
IX = pd.DataFrame({"m": ["2024-01", "2024-02", "2025-01"], "i": [100.0, 102.0, 110.0]})


def run(df, ix, **opts):
    return run_block(HERE, [df, ix], {**O, **opts})


def test_real_terms_and_base():
    df = pd.DataFrame({"d": ["2024-01-15", "2024-03-10", "2025-01-01", "2023-12-01"], "v": [100.0, 100.0, 100.0, 5.0]})
    o = run(df, IX).raise_for_error().output(0)
    assert np.allclose(o["v (real)"].iloc[:3], [110.0, 100 * 110 / 102, 100.0])
    assert o["Adjustment Status"].tolist() == ["Adjusted", "Adjusted", "Adjusted", "No index on or before date"]
    b = run(df, IX, base_period="2024-01").raise_for_error().output(0)
    assert np.isclose(b["v (real)"].iloc[2], 100 * 100 / 110)
    old = run(df, IX, max_age_days=30).raise_for_error().output(0)
    assert old["Adjustment Status"].iloc[1] == "Index too old"


def test_keys_and_index_table():
    ix = pd.DataFrame({"m": ["2024-01", "2025-01"] * 2, "i": [100.0, 110, 100, 103], "c": ["UK", "UK", "FR", "FR"]})
    df = pd.DataFrame({"d": ["2024-06-01", "2024-06-01"], "v": [100.0, 100.0], "c": ["UK", "FR"]})
    o = run(df, ix, key_field="c", index_key_field="c").raise_for_error()
    assert np.allclose(o.output(0)["v (real)"], [110.0, 103.0])
    t = o.output(1)
    assert np.isclose(t[(t["Key"] == "UK")]["Change From Year Before"].iloc[1], 0.10)
    assert run(df, ix, key_field="c").status == "aborted"


def test_sample_and_bad_inputs():
    res = run_block(HERE, [SAL, IDX], {"date_field": "Effective Date", "value_fields": ["Salary (GBP)"], "index_date_field": "Month",
                                       "index_value_field": "Price Index (illustrative)"}).raise_for_error()
    o = res.output(0)
    a = o[o["Role"] == "Analyst"]
    assert a["Salary (GBP) (real)"].iloc[0] > a["Salary (GBP)"].iloc[0] and (o["Adjustment Status"] == "Adjusted").all()
    assert run(pd.DataFrame({"d": ["2024-01-01"], "v": [1.0]}), IX.assign(i=[0, 1, 2])).status == "aborted"
    assert run(pd.DataFrame({"d": ["2024-01-01"], "v": [1.0]}), IX, base_period="1990-01").status == "aborted"
    assert run(pd.DataFrame({"d": ["2024-01-01"], "v": [1.0]}), IX, value_fields=[]).status == "aborted"
    big = pd.DataFrame({"d": (pd.Timestamp("2024-01-01") + pd.to_timedelta(np.random.default_rng(0).integers(0, 380, 300_000), unit="D")).strftime("%Y-%m-%d"),
                        "v": np.random.default_rng(1).gamma(2, 100, 300_000)})
    t0 = time.time()
    run(big, IX).raise_for_error()
    assert time.time() - t0 < 120
