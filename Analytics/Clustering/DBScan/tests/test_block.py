import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "customer-spend.csv")


def blobs(n_per_group=30, seed=0):
    """Three tight, well separated groups and two far-away points, with a text field."""
    rng = np.random.default_rng(seed)
    centres = [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]
    xs, ys, names = [], [], []
    for g, (cx, cy) in enumerate(centres):
        xs += list(rng.normal(cx, 0.3, n_per_group))
        ys += list(rng.normal(cy, 0.3, n_per_group))
        names += [f"g{g}"] * n_per_group
    xs += [30.0, -20.0]
    ys += [30.0, 25.0]
    names += ["far", "far"]
    return pd.DataFrame({"Group": names, "x": xs, "y": ys})


def test_sample_finds_three_groups_and_noise():
    res = run_block(HERE, SAMPLE, {}).raise_for_error()
    out = res.output(0)
    assert len(out) == 121
    assert list(out.columns) == ["Customer", "Region", "Annual Spend", "Visits Per Year", "Cluster"]
    counts = out["Cluster"].value_counts(dropna=False).to_dict()
    assert counts == {3: 45, 1: 39, 2: 30, 0: 6, pd.NA: 1}
    # the record with no visit count is kept, with an empty Cluster
    assert out.loc[out["Visits Per Year"].isna(), "Cluster"].isna().all()
    # the occasional buyers (low spend, few visits) form one cluster
    low = out[(out["Annual Spend"] < 500) & (out["Visits Per Year"] < 10)]
    assert set(low["Cluster"]) == {1}


def test_clusters_stay_on_their_records():
    df = blobs()
    out = run_block(HERE, df, {}).raise_for_error().output(0)
    assert len(out) == len(df)
    assert (out["Group"] == df["Group"]).all() and np.allclose(out["x"], df["x"])
    by_group = out.groupby("Group")["Cluster"].agg(lambda s: set(s))
    assert by_group["far"] == {0}  # noise is cluster 0
    assert {min(by_group[g]) for g in ("g0", "g1", "g2")} == {1, 2, 3}
    assert all(len(by_group[g]) == 1 for g in ("g0", "g1", "g2"))


def test_missing_values_keep_their_place():
    # The original block lost the alignment here: the record after a dropped one got the wrong cluster
    df = blobs()
    df.loc[5, "x"] = np.nan
    out = run_block(HERE, df, {}).raise_for_error().output(0)
    assert len(out) == len(df)
    assert pd.isna(out.loc[5, "Cluster"])
    assert out.loc[df["Group"] == "far", "Cluster"].tolist() == [0, 0]
    assert out["Group"].tolist() == df["Group"].tolist()


def test_chosen_fields_only():
    df = blobs()
    df["noise"] = np.random.default_rng(1).normal(0, 100, len(df))
    opts = {"useAllNumericFields": False, "fieldsToUse": ["x", "y"]}
    out = run_block(HERE, df, opts).raise_for_error().output(0)
    assert out.groupby("Group")["Cluster"].nunique().loc[["g0", "g1", "g2"]].tolist() == [1, 1, 1]


def test_integer_fields_are_numeric():
    df = pd.DataFrame({"a": [1, 1, 2, 1, 2, 100, 101, 100, 99, 100], "b": [2] * 10})
    out = run_block(HERE, df, {}).raise_for_error().output(0)  # integers arrive as Int64
    assert out["Cluster"].tolist() == [1] * 5 + [2] * 5


def test_existing_cluster_field_is_replaced():
    df = blobs()
    df["Cluster"] = "old"
    out = run_block(HERE, df, {"useAllNumericFields": False, "fieldsToUse": ["x", "y"]}).raise_for_error().output(0)
    assert list(out.columns).count("Cluster") == 1 and "old" not in set(out["Cluster"].astype(str))


def test_existing_numeric_cluster_field_is_not_clustered_on():
    """With "Use all numeric fields", a numeric Cluster field from an earlier run is replaced, not used: the
    result is the same as without it (it was clustered on, which split the groups by the old numbers)."""
    df = blobs()
    expected = run_block(HERE, df, {}).raise_for_error().output(0)["Cluster"].tolist()
    df["Cluster"] = (np.arange(len(df)) % 2) * 100  # clustering on it would split every group in two
    out = run_block(HERE, df, {}).raise_for_error().output(0)
    assert list(out.columns).count("Cluster") == 1
    assert out["Cluster"].tolist() == expected


def test_empty_input():
    df = blobs().iloc[:0]
    res = run_block(HERE, df, {}).raise_for_error()
    assert len(res.output(0)) == 0 and "Cluster" in res.output(0).columns


def test_wrong_types_and_missing_choices_abort():
    df = blobs()
    res = run_block(HERE, df, {"useAllNumericFields": False, "fieldsToUse": ["Group"]})
    assert res.status == "aborted" and "numeric" in res.final_message
    res = run_block(HERE, df, {"useAllNumericFields": False, "fieldsToUse": None})
    assert res.status == "aborted" and "Fields to cluster on" in res.final_message
    res = run_block(HERE, df[["Group"]], {})
    assert res.status == "aborted" and "no numeric fields" in res.final_message
    assert run_block(HERE, None, {}).status == "aborted"


def test_large_input():
    # Memory grows with the number of neighbours of each record (see the README); this checks 20,000 records in
    # well separated groups finish within 60 seconds.
    rng = np.random.default_rng(0)
    n = 20_000
    g = rng.integers(0, 4, n)
    df = pd.DataFrame({"id": np.arange(n), "x": rng.normal(g * 50.0, 1.0), "y": rng.normal(g * 40.0, 1.0)})
    t0 = time.time()
    out = run_block(HERE, df, {"useAllNumericFields": False, "fieldsToUse": ["x", "y"]}).raise_for_error().output(0)
    assert time.time() - t0 < 60 and len(out) == n
    assert out["Cluster"].nunique() == 4
