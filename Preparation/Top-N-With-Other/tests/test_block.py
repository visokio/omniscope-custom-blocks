import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "regional-sales.csv")
DF = pd.DataFrame({"g": ["x"] * 5 + ["y"] * 2, "i": ["a", "b", "c", "d", "a", "p", "q"], "v": [50.0, 30, 10, 5, 5, 8, 2], "u": [1, 2, 3, 4, 5, 6, 7]})


def run(df, **opts):
    return run_block(HERE, df, {"item_field": "i", "value_field": "v", **opts})


def test_top_n_and_other():
    o = run(DF, group_fields=["g"], top_n=2, extra_value_fields=["u"]).raise_for_error().output(0)
    x = o[o["g"] == "x"]
    assert x["i"].tolist() == ["a", "b", "Other"] and x["v"].tolist() == [55.0, 30.0, 15.0] and x["u"].tolist() == [6.0, 2.0, 7.0]
    assert x["Items Included"].tolist() == [1, 1, 2] and np.isclose(x["Cumulative Share"].iloc[1], 0.85) and x["Cumulative Share"].iloc[-1] == 1.0
    assert o[o["g"] == "y"]["i"].tolist() == ["p", "q"]  # nothing left for Other


def test_min_share_no_other_and_label():
    o = run(DF, top_n=0, min_share=0.2).raise_for_error().output(0)
    assert o["i"].tolist() == ["a", "b", "Other"]
    o = run(DF, top_n=3, include_other=False).raise_for_error().output(0)
    assert "Other" not in set(o["i"]) and len(o) == 3
    o = run(DF, top_n=1, other_label="All others").raise_for_error().output(0)
    assert o["i"].tolist() == ["a", "All others"]


def test_sample_and_bad_inputs():
    o = run_block(HERE, SAMPLE, {"item_field": "Product", "value_field": "Revenue (GBP)", "group_fields": ["Region"], "top_n": 5}).raise_for_error().output(0)
    assert len(o) == 24 and (o.groupby("Region")["Share Of Group"].sum().round(9) == 1.0).all()
    assert run(DF, value_field="zz").status == "aborted"
    assert run(DF.assign(v="x")).status == "aborted"
    assert run(DF, top_n=0).status == "aborted"
    big = pd.DataFrame({"g": np.random.default_rng(0).choice(list("abcdefgh"), 300_000), "i": np.random.default_rng(1).integers(0, 5000, 300_000).astype(str),
                        "v": np.random.default_rng(2).gamma(2, 10, 300_000)})
    t0 = time.time()
    assert len(run(big, group_fields=["g"]).raise_for_error().output(0)) == 88 and time.time() - t0 < 120
