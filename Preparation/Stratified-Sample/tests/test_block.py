import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "invoice-population.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, opts)


def pop():
    return pd.DataFrame({"g": ["a"] * 90 + ["b"] * 9 + ["c"] * 1, "id": range(100)})


def test_proportional_with_minimum():
    res = run(pop(), strata_fields=["g"], total_n=20, min_per_stratum=2).raise_for_error()
    a = res.output(2).set_index("g")
    assert a["Sample Size"].to_dict() == {"a": 17, "b": 2, "c": 1}
    s = res.output(0)
    assert len(s) == 20 and s["id"].is_unique
    assert abs(s.loc[s.g == "a", "Sample Weight"].iloc[0] - 90 / 17) < 1e-9
    assert len(res.output(1)) == 80 and set(res.output(1)["id"]).isdisjoint(set(s["id"]))


def test_equal_fixed_percent():
    a = run(pop(), strata_fields=["g"], method="EQUAL", total_n=12).raise_for_error().output(2).set_index("g")["Sample Size"]
    assert a.sum() == 12 and a["c"] == 1 and a["b"] in (5, 6)
    f = run(pop(), strata_fields=["g"], method="FIXED", per_stratum_n=5).raise_for_error().output(2).set_index("g")["Sample Size"]
    assert f.to_dict() == {"a": 5, "b": 5, "c": 1}
    p = run(pop(), strata_fields=["g"], method="PERCENT", percent=10).raise_for_error().output(2).set_index("g")["Sample Size"]
    assert p.to_dict() == {"a": 9, "b": 1, "c": 0}


def test_seed_reproducible():
    a = run(pop(), strata_fields=["g"], total_n=20, seed=7).raise_for_error().output(0)["id"].tolist()
    b = run(pop(), strata_fields=["g"], total_n=20, seed=7).raise_for_error().output(0)["id"].tolist()
    c = run(pop(), strata_fields=["g"], total_n=20, seed=8).raise_for_error().output(0)["id"].tolist()
    assert a == b and a != c


def test_no_strata_and_oversized_sample():
    res = run(pop(), total_n=1000).raise_for_error()
    assert len(res.output(0)) == 100 and len(res.output(1)) == 0 and res.output(0)["Stratum"].iloc[0] == "All"


def test_sample_population():
    res = run_block(HERE, SAMPLE, {"strata_fields": ["Region", "Risk Band"], "total_n": 150, "min_per_stratum": 3}).raise_for_error()
    a = res.output(2)
    assert len(a) == 15 and a["Sample Size"].sum() == 150 and (a["Sample Size"] >= 3).all()
    s = res.output(0)
    assert abs(s["Sample Weight"].sum() - 4000) < 1e-6  # weights reproduce the population size


def test_bad_options_and_empty():
    assert run(pop(), strata_fields=["g"], total_n=2, min_per_stratum=2).status == "aborted"
    assert run(pop(), strata_fields=["nope"]).status == "aborted"
    res = run(pop().iloc[0:0], strata_fields=["g"]).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(2)) == 0


def test_nulls_in_strata():
    df = pd.DataFrame({"g": ["a", None, None, "a"], "id": range(4)})
    a = run(df, strata_fields=["g"], method="FIXED", per_stratum_n=1).raise_for_error().output(2)
    assert set(a["g"]) == {"a", "(blank)"}


def test_large_input_is_fast():
    n = 1_000_000
    df = pd.DataFrame({"g": np.arange(n) % 500, "id": np.arange(n)})
    t0 = time.time()
    res = run(df, strata_fields=["g"], total_n=10_000, min_per_stratum=5).raise_for_error()
    assert time.time() - t0 < 60 and len(res.output(0)) == 10_000
