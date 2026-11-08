import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "card-transactions.csv")
DF = pd.DataFrame({"k": ["a", "a", "a", "b", "a"], "t": ["2025-01-01 10:00", "2025-01-01 10:30", "2025-01-01 12:00", "2025-01-01 10:10", "2025-01-02 10:00"],
                   "v": [1.0, 2.0, 4.0, 100.0, 8.0], "m": ["x", "y", "x", "z", "w"]})


def run(df, **opts):
    return run_block(HERE, df, {"key_field": "k", "time_field": "t", **opts})


def test_windows_counts_sums():
    o = run(DF, value_field="v", distinct_field="m", windows="1h, 24h").raise_for_error().output(0)
    assert o["Count 1h"].tolist() == [1, 2, 1, 1, 1] and o["Sum 1h"].tolist() == [1.0, 3.0, 4.0, 100.0, 8.0]
    assert o["Count 24h"].tolist() == [1, 2, 3, 1, 3]  # window (t - 24h, t]: 1 Jan 10:00 drops out of 2 Jan 10:00
    assert o["Max 24h"].iloc[2] == 4.0 and o["Distinct m 24h"].iloc[2] == 2


def test_exclude_current_and_bad_windows():
    o = run(DF, value_field="v", windows="24h", include_current=False).raise_for_error().output(0)
    assert o["Count 24h"].tolist() == [0, 1, 2, 0, 2] and pd.isna(o["Mean 24h"].iloc[0])
    assert run(DF, windows="soon").status == "aborted"
    assert run(DF, key_field="zz").status == "aborted"


def test_sample_and_large():
    o = run_block(HERE, SAMPLE, {"key_field": "Card", "time_field": "Time", "value_field": "Amount (GBP)", "distinct_field": "Merchant", "windows": "1h, 24h"}).raise_for_error().output(0)
    assert o["Count 1h"].max() >= 9 and o["Distinct Merchant 1h"].max() >= 9
    rng = np.random.default_rng(0)
    big = pd.DataFrame({"k": rng.integers(0, 5000, 300_000).astype(str), "t": pd.Timestamp("2025-01-01") + pd.to_timedelta(rng.integers(0, 10**7, 300_000), unit="s"),
                        "v": rng.gamma(2, 10, 300_000)})
    t0 = time.time()
    run(big, value_field="v", windows="1h, 7d").raise_for_error()
    assert time.time() - t0 < 120
