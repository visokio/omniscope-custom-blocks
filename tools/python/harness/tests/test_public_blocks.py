"""Prove the harness against blocks in this repository that predate it."""
import os

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
PB = {name: os.path.join(REPO, "Preparation", *path) for name, path in {
    "Partition": ["Partition"], "Add-row-ID-field": ["Add-row-ID-field"],
    "Melt-De-pivot": ["Pivot", "Melt-De-pivot"], "Data-Quality-Analyser": ["Data-Quality-Analyser"],
}.items()}


@pytest.fixture
def sales():
    return pd.DataFrame({
        "Region": ["North", "South", "North", "East", "East", "North"],
        "Q1": [10.0, 20.0, 10.0, np.nan, 5.0, 900.0],
        "Q2": [11.0, 21.0, 11.0, 7.0, 6.0, 12.0],
    })


def test_partition_streaming(sales):
    res = run_block(PB["Partition"], sales, {"partition_size": 4}).raise_for_error()
    out = res.output(0)
    assert [int(v) for v in out["Partition"]] == [1, 1, 1, 1, 2, 2]  # an Integer field since the refresh (it was text)


def test_add_row_id_streaming(sales):
    res = run_block(PB["Add-row-ID-field"], sales, {"fieldName": "RID"}).raise_for_error()
    assert "RID" in res.output(0).columns
    assert len(res.output(0)) == len(sales)


def test_melt_depivot(sales):
    res = run_block(PB["Melt-De-pivot"], sales, {"fixed_fields": ["Region"]}).raise_for_error()
    out = res.output(0)
    assert len(out) == 12
    assert set(out["Field"]) == {"Q1", "Q2"}


def test_data_quality_analyser_multi_output(sales):
    res = run_block(PB["Data-Quality-Analyser"], sales,
                    {"enrichData": True}).raise_for_error()
    # outputs addressed by number in the script; three outputs declared in the manifest
    assert set(res.outputs) == {0, 1, 2}
    issues = res.output(1)
    assert {"DUPLICATE_ROW", "MISSING_VALUE", "OUTLIER"} <= set(issues["Issue Type"])


def test_unknown_option_is_rejected(sales):
    with pytest.raises(KeyError):
        run_block(PB["Partition"], sales, {"partition_sise": 4})


def test_abort_is_recorded(tmp_path):
    script = tmp_path / "script.py"
    script.write_text("from omniscope.api import OmniscopeApi\napi=OmniscopeApi()\napi.abort('boom')\nraise RuntimeError('should not run')\n")
    res = run_block(str(tmp_path), None, {}, script=str(script))
    assert res.status == "aborted" and res.final_message == "boom" and res.error is None


def test_schema_change_between_writes_is_an_error(tmp_path):
    script = tmp_path / "script.py"
    script.write_text(
        "from omniscope.api import OmniscopeApi\nimport pandas as pd\napi=OmniscopeApi()\n"
        "api.write_output_records(pd.DataFrame({'a':[1]}))\n"
        "api.write_output_records(pd.DataFrame({'b':[1]}))\napi.close()\n")
    res = run_block(str(tmp_path), None, {}, script=str(script))
    assert res.error is not None and "schema changed" in str(res.error)
