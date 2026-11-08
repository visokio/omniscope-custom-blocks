"""Tests for the XPT Reader block. The sample file is written by sample-data/make_sample_xpt.py; two independent
checks guard against the reader and that writer sharing a mistake: pandas' own XPORT reader must agree on the first
dataset, and tests/canned/written-by-xport-package.xpt was written by the third-party xport package."""
import importlib.util
import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "trial-sample.xpt")
BY_XPORT = os.path.join(HERE, "tests", "canned", "written-by-xport-package.xpt")

spec = importlib.util.spec_from_file_location("make_sample_xpt", os.path.join(HERE, "sample-data", "make_sample_xpt.py"))
writer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writer)


def read(path, **options):
    return run_block(HERE, None, {"xptFile": str(path), **options})


def test_sample_first_dataset_with_summary_and_fields():
    res = read(SAMPLE).raise_for_error()
    summary, records, fields = res.output(0), res.output(1), res.output(2)
    assert summary["Dataset Name"].tolist() == ["ADSL", "VS"]
    assert summary["Records"].tolist() == [24, 138]
    assert summary["Label"].tolist() == ["Subject-level analysis data", "Vital signs"]
    assert summary["Fields"][1] == "USUBJID, VISIT, VSTESTCD, VSSTRESN, VSSTRESU, VSDT"
    assert summary["Created"][0] == pd.Timestamp("2025-06-30 09:15:00")
    assert len(records) == 24
    assert list(records.columns) == ["STUDYID", "USUBJID", "SITE", "SEX", "AGE", "ARM", "TRTSDT", "WEIGHTBL", "SAFFL"]
    assert records["USUBJID"].iloc[0] == "DEMO-01-101" and records["SITE"].iloc[3] == "Cardiff"
    # DATE9. numbers become dates; the subject never treated has none
    assert pd.api.types.is_datetime64_any_dtype(records["TRTSDT"])
    assert records["TRTSDT"].iloc[0] == pd.Timestamp("2025-02-04") and pd.isna(records["TRTSDT"].iloc[23])
    assert records["WEIGHTBL"].isna().sum() == 2 and records["WEIGHTBL"].iloc[0] == 72.5
    assert len(fields) == 15
    trtsdt = fields[(fields["Dataset Name"] == "ADSL") & (fields["Field"] == "TRTSDT")].iloc[0]
    assert (trtsdt["Label"], trtsdt["Format"], trtsdt["Read as"]) == ("Date of first dose", "DATE9.", "Date")
    assert fields.loc[fields["Field"] == "WEIGHTBL", "Format"].tolist() == ["8.1"]
    assert "24 records" in res.final_message


def test_agrees_with_pandas_own_reader_on_the_first_dataset():
    ours = read(SAMPLE, convertDates=False).raise_for_error().output(1)
    ref = pd.read_sas(SAMPLE, format="xport").iloc[:24]  # pandas reads only the first dataset (and runs on)
    for col in ref.columns:
        if ref[col].dtype == object:
            assert ours[col].tolist() == [b.decode().rstrip() for b in ref[col]], col
        else:
            np.testing.assert_array_equal(ours[col].to_numpy(dtype=float), ref[col].to_numpy(dtype=float))


def test_reads_both_datasets_of_a_file_written_by_the_xport_package():
    res = read(BY_XPORT).raise_for_error()
    first = res.output(1)
    assert first["ID"].tolist() == ["A1", "B22", "C333"]
    assert first["SCORE"].iloc[0] == 1.5 and pd.isna(first["SCORE"].iloc[1])
    assert first["SCORE"].iloc[2] == pytest.approx(-1234.5678, abs=1e-9)
    assert first["N"].tolist() == [0.0, 1e10, 3.0]
    second = read(BY_XPORT, datasetName="SECOND").raise_for_error().output(1)
    assert second["CODE"].tolist() == ["x", "yy"] and second["VAL"].tolist() == pytest.approx([0.1, 7.0])


def test_dataset_name_ignores_case_and_empty_means_first():
    # The original block aborted on "vs" (names are upper case in the file) and on a cleared option ("")
    vs = read(SAMPLE, datasetName="vs").raise_for_error().output(1)
    assert len(vs) == 138 and vs["VSDT"].iloc[2] == pd.Timestamp("2025-03-04")
    assert vs["VSSTRESN"].isna().sum() == 2
    assert len(read(SAMPLE, datasetName="").raise_for_error().output(1)) == 24
    assert len(read(SAMPLE, datasetName="  ").raise_for_error().output(1)) == 24


def test_unknown_dataset_aborts_with_the_names_in_the_file():
    res = read(SAMPLE, datasetName="AE")
    assert res.status == "aborted" and "ADSL, VS" in res.final_message


def test_dates_can_stay_sas_numbers():
    res = read(SAMPLE, convertDates=False).raise_for_error()
    assert res.output(1)["TRTSDT"].iloc[0] == 23776.0  # days since 1 January 1960
    assert res.output(2).loc[res.output(2)["Field"] == "TRTSDT", "Read as"].tolist() == ["Number"]


def test_datetime_formats_and_special_missing_values(tmp_path):
    df = pd.DataFrame({"WHEN": [2054246400.0, float("nan")], "CODE": ["a", "b"], "N": [1.0, 2.0]})
    path = tmp_path / "dt.xpt"
    writer.write_xpt(path, [("EVENTS", "", df, {"WHEN": "", "CODE": "", "N": ""}, {"WHEN": "E8601DT19."})])
    data = bytearray(path.read_bytes())
    # turn the second N value into the SAS special missing value .A
    marker = data.find(writer.ibm(2.0))
    data[marker:marker + 8] = b"A" + b"\x00" * 7
    path.write_bytes(bytes(data))
    out = read(path).raise_for_error().output(1)
    assert out["WHEN"].iloc[0] == pd.Timestamp("2025-02-04") and pd.isna(out["WHEN"].iloc[1])
    assert out["N"].iloc[0] == 1.0 and pd.isna(out["N"].iloc[1])


def test_short_records_do_not_turn_padding_into_records(tmp_path):
    path = tmp_path / "short.xpt"
    writer.write_xpt(path, [("FLAGS", "", pd.DataFrame({"F": ["a", "b", "c"]}), {"F": ""}, {})])
    assert read(path).raise_for_error().output(1)["F"].tolist() == ["a", "b", "c"]


def test_dataset_with_no_records(tmp_path):
    path = tmp_path / "empty.xpt"
    empty = pd.DataFrame({"ID": pd.Series([], dtype=object), "X": pd.Series([], dtype=float)})
    writer.write_xpt(path, [("EMPTY", "No rows", empty, {"ID": "", "X": ""}, {})])
    res = read(path).raise_for_error()
    assert len(res.output(1)) == 0 and list(res.output(1).columns) == ["ID", "X"]
    assert res.output(0)["Records"].tolist() == [0]


def test_wrong_files_abort_with_a_message(tmp_path):
    res = run_block(HERE, None, {"xptFile": None})
    assert res.status == "aborted" and "Choose" in res.final_message
    assert read(tmp_path / "missing.xpt").status == "aborted"
    csv = tmp_path / "data.csv"
    csv.write_text("a,b\n1,2\n")
    res = read(csv)
    assert res.status == "aborted" and "not a SAS transport file" in res.final_message
    cport = tmp_path / "cport.xpt"
    cport.write_bytes(b"**COMPRESSED** **COMPRESSED** **COMPRESSED**".ljust(160))
    assert "PROC CIMPORT" in read(cport).final_message
    v8 = tmp_path / "v8.xpt"
    v8.write_bytes(b"HEADER RECORD*******LIBV8   HEADER RECORD!!!!!!!".ljust(160))
    assert "version 8" in read(v8).final_message


def test_large_dataset(tmp_path):
    n = 100_000
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"ID": [f"S{i:06d}" for i in range(n)], "X": rng.normal(size=n), "D": rng.integers(0, 30000, n) * 1.0})
    path = tmp_path / "large.xpt"
    # write the records directly (the sample writer's row loop is slow at this size)
    small = df.iloc[:1]
    writer.write_xpt(path, [("BIG", "", small, {"ID": "", "X": "", "D": ""}, {"D": "DATE9."})])
    head = path.read_bytes()
    head = head[:head.rfind(b"HEADER RECORD*******OBS") + 80]
    ids = df["ID"].str.encode("latin-1")
    rows = b"".join(i + writer.ibm(x) + writer.ibm(d) for i, x, d in zip(ids, df["X"], df["D"]))
    path.write_bytes(head + rows + b" " * (-len(rows) % 80))
    t0 = time.time()
    out = read(path).raise_for_error().output(1)
    assert time.time() - t0 < 30
    assert len(out) == n and out["ID"].iloc[-1] == "S099999"
    np.testing.assert_allclose(out["X"].to_numpy(), df["X"].to_numpy(), rtol=1e-15)


def test_placeholder_is_the_block_output_for_the_sample():
    # The demo shows sample-data/placeholder.csv in place of the block's Dataset output: it must stay identical.
    records = read(SAMPLE).raise_for_error().output(1)
    expected = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"), parse_dates=["TRTSDT"])
    expected["TRTSDT"] = expected["TRTSDT"].astype(records["TRTSDT"].dtype)  # same values, s vs us resolution
    pd.testing.assert_frame_equal(records.reset_index(drop=True), expected, check_dtype=False)
