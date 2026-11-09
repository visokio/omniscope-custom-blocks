"""Kedro block tests.

Most tests use a stand-in for Kedro (tests/fake_kedro.py) and run anywhere. The last two run the small real Kedro
project in tests/kedro-project/ (copied to a temporary folder) and are skipped when kedro and kedro-datasets are
not installed."""
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
TESTS = os.path.join(HERE, "tests")
ORDERS = os.path.join(HERE, "sample-data", "orders.csv")
TARGETS = os.path.join(HERE, "sample-data", "region-targets.csv")
PLACEHOLDER = os.path.join(HERE, "sample-data", "placeholder.csv")
sys.path.insert(0, TESTS)
import fake_kedro  # noqa: E402

SAMPLE_OPTIONS = {"input0": "orders", "input1": "targets", "output0": "region_summary"}


def summarise(catalog, pipeline_name):
    """What the test project's default pipeline does, written against the fake catalog."""
    orders = catalog.load("orders")
    orders = orders[orders["Status"] != "Cancelled"].copy()
    orders["Value"] = orders["Quantity"].astype(float) * orders["Unit Price"].astype(float)
    out = orders.groupby("Region", as_index=False).agg(Orders=("Order", "nunique"), Sales=("Value", "sum"))
    out = out.merge(catalog.load("targets"), on="Region", how="left")
    catalog.save("region_summary", out)
    return {}


@pytest.fixture
def project(tmp_path):
    """An empty folder that passes the block's Kedro-project check."""
    (tmp_path / "pyproject.toml").write_text('[tool.kedro]\npackage_name = "demo"\n')
    return tmp_path


def run(project, inputs, options, datasets=None, pipeline=summarise, monkeypatch=None):
    fake_kedro.install(monkeypatch, {} if datasets is None else datasets, pipeline)
    return run_block(HERE, inputs, {"path": str(project), **options})


def test_sample_inputs_go_to_the_catalog_and_the_output_comes_back(project, monkeypatch):
    datasets = {"orders": None, "targets": None, "region_summary": None}
    res = run(project, [ORDERS, TARGETS], SAMPLE_OPTIONS, datasets, monkeypatch=monkeypatch).raise_for_error()
    out = res.output(0)
    assert out["Region"].tolist() == ["Midlands", "North", "South East", "South West", "Wales"]
    assert out["Orders"].tolist() == [7, 5, 6, 9, 5]
    assert len(datasets["orders"]) == 40 and len(datasets["targets"]) == 5
    # the input reaches Kedro with Omniscope's types (Int64 numbers, UTC dates), unchanged
    assert str(datasets["orders"]["Quantity"].dtype) == "Int64"
    assert str(datasets["orders"]["Order Date"].dtype).endswith("UTC]")
    names = [c[0] for c in fake_kedro.calls]
    # the block's calls, with the pipeline's own load/load/save between run and the block's final load
    assert names == ["bootstrap", "create", "save", "save", "run", "load", "load", "save", "load", "close"]
    assert ("create", str(project), None) in fake_kedro.calls and ("run", None) in fake_kedro.calls
    assert res.output(1) is None and "1 dataset" in res.final_message


def test_free_outputs_pipeline_and_environment(project, monkeypatch):
    def pipeline(catalog, name):
        df = catalog.load("orders")
        return {"shipped": df[df["Status"] == "Shipped"], "counts": df["Status"].value_counts()}

    res = run(project, ORDERS, {"input0": "orders", "output0": "shipped", "output1": "counts",
                                "pipeline": " shipping ", "env": "prod"}, {"orders": None},
              pipeline, monkeypatch).raise_for_error()
    assert ("run", "shipping") in fake_kedro.calls and ("create", str(project), "prod") in fake_kedro.calls
    assert set(res.output(0)["Status"]) == {"Shipped"}
    assert res.output(0).index.tolist() == list(range(len(res.output(0))))
    assert res.output(1)["count"].sum() == 40  # a Series becomes a one-field table


def test_dataset_objects_returned_by_the_run_are_loaded(project, monkeypatch):
    class Dataset:
        def load(self):
            return pd.DataFrame({"a": [1, 2]})

    res = run(project, None, {"input0": "", "output0": "result"}, {}, lambda c, n: {"result": Dataset()},
              monkeypatch).raise_for_error()
    assert res.output(0)["a"].tolist() == [1, 2]


def test_names_outside_the_catalog_use_the_data_folders(project, monkeypatch):
    # The original block deleted data/01_raw/<name>.csv before writing it, and crashed when it wasn't there yet
    def pipeline(catalog, name):
        raw = pd.read_csv(project / "data" / "01_raw" / "orders.csv")
        (project / "data" / "08_reporting").mkdir(parents=True)
        raw.groupby("Region", as_index=False).size().to_csv(project / "data" / "08_reporting" / "sizes.csv",
                                                              index=False)
        return {}

    res = run(project, ORDERS, {"input0": "orders", "output0": "sizes"}, {}, pipeline,
              monkeypatch).raise_for_error()
    assert (project / "data" / "01_raw" / "orders.csv").exists()
    assert res.output(0)["size"].sum() == 40


def test_existing_raw_file_is_replaced(project, monkeypatch):
    raw = project / "data" / "01_raw"
    raw.mkdir(parents=True)
    (raw / "orders.csv").write_text("old\n1\n")
    run(project, ORDERS, {"input0": "orders", "output0": "orders"}, {}, lambda c, n: {"orders": pd.DataFrame()},
        monkeypatch).raise_for_error()
    assert len(pd.read_csv(raw / "orders.csv")) == 40


def test_empty_input(project, monkeypatch):
    empty = pd.read_csv(ORDERS).iloc[:0]
    datasets = {"orders": None}
    res = run(project, empty, {"input0": "orders", "output0": "orders"}, datasets,
              lambda c, n: {}, monkeypatch).raise_for_error()
    assert len(datasets["orders"]) == 0
    assert len(res.output(0)) == 0 and "Region" in res.output(0).columns


@pytest.mark.parametrize("make, options, inputs, expected", [
    (False, {"path": None}, None, "Choose the folder"),
    ("none", {}, None, "No pyproject.toml"),
    ("plain", {}, None, "no [tool.kedro] section"),
    (True, {"input1": "targets"}, [ORDERS], "nothing is connected to input 2"),
    (True, {"input1": ""}, [ORDERS, TARGETS], "Input 2 is connected"),
    (True, {"output0": " "}, [ORDERS, TARGETS], "Output dataset 1"),
    (True, {"output0": "missing"}, [ORDERS, TARGETS], "'missing' is not in the project's catalog"),
])
def test_bad_settings_abort_with_a_message(tmp_path, monkeypatch, make, options, inputs, expected):
    if make is True:
        (tmp_path / "pyproject.toml").write_text("[tool.kedro]\n")
    elif make == "plain":
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
    fake_kedro.install(monkeypatch, {"orders": None, "targets": None, "region_summary": None}, summarise)
    opts = {"path": str(tmp_path), **SAMPLE_OPTIONS, **options}
    res = run_block(HERE, inputs, opts)
    assert res.error is None and res.status == "aborted"
    assert expected in res.final_message


def test_failed_run_and_unloadable_project_report_kedro_reason(project, monkeypatch):
    def broken(catalog, name):
        raise KeyError("Region")

    res = run(project, [ORDERS, TARGETS], SAMPLE_OPTIONS, {"orders": None, "targets": None}, broken, monkeypatch)
    assert res.status == "aborted" and "The Kedro run failed: KeyError: 'Region'" in res.final_message
    fake_kedro.install(monkeypatch, {}, summarise)
    fake_kedro.state["bootstrap_error"] = ValueError("version 0.18 does not match")
    res = run_block(HERE, [ORDERS, TARGETS], {"path": str(project), **SAMPLE_OPTIONS})
    assert res.status == "aborted" and "version 0.18 does not match" in res.final_message


def test_kedro_missing_and_non_table_output(project, monkeypatch):
    fake_kedro.install(monkeypatch, {}, summarise)
    monkeypatch.setitem(sys.modules, "kedro.framework.session", None)  # import fails, as without Kedro
    res = run_block(HERE, [ORDERS, TARGETS], {"path": str(project), **SAMPLE_OPTIONS})
    assert res.status == "aborted" and "Kedro is not installed" in res.final_message
    res = run(project, None, {"input0": "", "output0": "model"}, {}, lambda c, n: {"model": {"weights": [1]}},
              monkeypatch)
    assert res.status == "aborted" and "is a dict, not a table" in res.final_message


def test_large_input(project, monkeypatch):
    n = 300_000
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"Order": np.arange(n), "Region": rng.choice(["N", "S"], n),
                       "Quantity": rng.integers(1, 9, n), "Unit Price": rng.random(n), "Status": "Shipped"})
    datasets = {"orders": None, "targets": pd.DataFrame({"Region": ["N", "S"], "Target": [1, 1]}),
                "region_summary": None}
    start = time.time()
    res = run(project, df, {"input0": "orders", "output0": "region_summary"}, datasets,
              monkeypatch=monkeypatch).raise_for_error()
    assert res.output(0)["Orders"].sum() == n and time.time() - start < 20


# ---- the real Kedro project in tests/kedro-project

def real_project(tmp_path):
    pytest.importorskip("kedro")
    pytest.importorskip("kedro_datasets")
    dest = tmp_path / "kedro-project"
    shutil.copytree(os.path.join(TESTS, "kedro-project"), dest)
    return dest


def test_real_kedro_project_sample_matches_placeholder(tmp_path):
    dest = real_project(tmp_path)
    res = run_block(HERE, [ORDERS, TARGETS], {"path": str(dest), **SAMPLE_OPTIONS}).raise_for_error()
    out = res.output(0)
    expected = pd.read_csv(PLACEHOLDER)
    pd.testing.assert_frame_equal(out.reset_index(drop=True), expected, check_dtype=False)
    assert out["Target met"].tolist() == [True, False, True, True, False]
    assert len(pd.read_csv(dest / "data" / "01_raw" / "orders.csv")) == 40


def test_real_kedro_named_pipeline_free_output(tmp_path):
    dest = real_project(tmp_path)
    res = run_block(HERE, [ORDERS], {"path": str(dest), "input0": "orders", "output0": "clean_orders",
                                     "pipeline": "clean"}).raise_for_error()
    out = res.output(0)
    cancelled = (pd.read_csv(ORDERS)["Status"] == "Cancelled").sum()
    assert len(out) == 40 - cancelled and "Cancelled" not in set(out["Status"])
    res = run_block(HERE, [ORDERS], {"path": str(dest), "input0": "orders", "output0": "x", "pipeline": "nope"})
    assert res.status == "aborted" and "The Kedro run failed" in res.final_message
