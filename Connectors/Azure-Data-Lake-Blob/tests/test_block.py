"""Azure Data Lake Storage Gen2 Blob block tests. No call reaches Azure: a stand-in `azure.storage.blob` module
serves canned files (sample-data/placeholder.csv, tests/mixed-types.parquet) and records what the block asked for."""
import gzip
import io
import json
import os
import sys
import time
import types

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "placeholder.csv")
MIXED = os.path.join(HERE, "tests", "mixed-types.parquet")
CONN = "DefaultEndpointsProtocol=https;AccountName=examplestore;AccountKey=ZmFrZQ==;EndpointSuffix=core.windows.net"


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


class ResourceNotFoundError(Exception):
    pass


class ClientAuthenticationError(Exception):
    pass


class FakeAzure:
    """Stands in for azure.storage.blob: blobs are {(container, path): bytes}."""

    def __init__(self, blobs, connect_error=None):
        self.blobs = blobs
        self.requests = []
        self.connection_strings = []
        fake = self

        class Download:
            def __init__(self, data):
                self.data = data

            def readall(self):
                return self.data

        class BlobClient:
            def __init__(self, container, path):
                self.container, self.path = container, path

            def download_blob(self):
                fake.requests.append((self.container, self.path))
                if (self.container, self.path) not in fake.blobs:
                    raise ResourceNotFoundError("The specified blob does not exist.\nRequestId:0000")
                return Download(fake.blobs[(self.container, self.path)])

        class ContainerClient:
            def __init__(self, container):
                self.container = container

            def get_blob_client(self, path):
                return BlobClient(self.container, path)

        class BlobServiceClient:
            @classmethod
            def from_connection_string(cls, conn):
                fake.connection_strings.append(conn)
                if connect_error:
                    raise connect_error
                return cls()

            def get_container_client(self, container):
                return ContainerClient(container)

        self.module = types.ModuleType("azure.storage.blob")
        self.module.BlobServiceClient = BlobServiceClient


@pytest.fixture
def azure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # the original saved the blob in the working folder; check nothing lands here

    def install(blobs, connect_error=None):
        fake = FakeAzure(blobs, connect_error)
        pkg, storage = types.ModuleType("azure"), types.ModuleType("azure.storage")
        pkg.storage, storage.blob = storage, fake.module
        monkeypatch.setitem(sys.modules, "azure", pkg)
        monkeypatch.setitem(sys.modules, "azure.storage", storage)
        monkeypatch.setitem(sys.modules, "azure.storage.blob", fake.module)
        return fake
    return install


def opts(path, **kw):
    return {"connectionString": CONN, "containerName": "retail", "blobPath": path, **kw}


def test_reads_a_csv_blob(azure, tmp_path):
    fake = azure({("retail", "sales/2026/march.csv"): read(SAMPLE)})
    res = run_block(HERE, None, opts("sales/2026/march.csv")).raise_for_error()
    out = res.output(0)
    assert len(out) == 30
    assert list(out.columns) == ["Date", "Store", "Region", "Units", "Revenue", "Promotion"]
    assert fake.requests == [("retail", "sales/2026/march.csv")] and fake.connection_strings == [CONN]
    # True/False stay booleans (the original turned them into the text "TRUE"/"FALSE" for CSV only)
    assert out["Promotion"].dtype == bool and out["Promotion"].sum() == 9
    assert out["Units"].sum() == 2204
    assert os.listdir(tmp_path) == []  # the original left march.csv in the working folder


def test_reads_parquet_and_makes_types_omniscope_can_hold(azure):
    azure({("retail", "tills/mixed.parquet"): read(MIXED)})
    out = run_block(HERE, None, opts("tills/mixed.parquet")).raise_for_error().output(0)
    assert out["Store"].tolist() == ["Leeds Kirkgate", "York Micklegate", "Leeds Kirkgate"]
    assert out["Price"].tolist()[:2] == [9.99, 12.5] and pd.isna(out["Price"].iloc[2])
    assert out["Basket"].tolist() == ['["tea", "scone"]', '["jam"]', "[]"]
    assert json.loads(out["Till"].iloc[0])["staff"] == "AB" and pd.isna(out["Till"].iloc[2])
    assert out["Dwell"].tolist()[:2] == [90.0, 45.0]
    assert pd.api.types.is_datetime64_any_dtype(out["Sold at"])
    assert str(out["Units"].dtype) == "Int64"


def test_file_type_from_the_extension_and_gzip(azure):
    blobs = {("retail", "a/data.parquet"): read(SAMPLE)}  # CSV content under a Parquet name
    blobs[("retail", "a/data.csv.gz")] = gzip.compress(read(SAMPLE))
    blobs[("retail", "a/data.tsv")] = pd.read_csv(SAMPLE).to_csv(sep="\t", index=False).encode()
    azure(blobs)
    assert len(run_block(HERE, None, opts("a/data.csv.gz")).raise_for_error().output(0)) == 30
    out = run_block(HERE, None, opts("a/data.tsv")).raise_for_error().output(0)
    assert len(out) == 30 and "Store" in out.columns
    # CSV content named .parquet: the Parquet reader fails, with a pointer to the file type option
    res = run_block(HERE, None, opts("a/data.parquet"))
    assert res.status == "aborted" and "as Parquet" in res.final_message and "file type" in res.final_message
    # but a chosen file type wins over the extension
    assert len(run_block(HERE, None, opts("a/data.parquet", fileType="CSV")).raise_for_error().output(0)) == 30
    res = run_block(HERE, None, opts("a/data.xlsx"))
    assert res.status == "aborted" and "choose CSV or Parquet" in res.final_message


def test_missing_blob_and_bad_connection_string_abort_with_a_message(azure):
    azure({})
    res = run_block(HERE, None, opts("sales/none.csv"))
    assert res.status == "aborted" and "ResourceNotFoundError" in res.final_message
    assert res.final_message == ("Could not read retail/sales/none.csv: ResourceNotFoundError: The specified blob does "
                                 "not exist. Check the container name and the blob path (they are case-sensitive).")
    azure({}, connect_error=ValueError("Connection string missing required connection details."))
    res = run_block(HERE, None, opts("sales/none.csv"))
    assert res.status == "aborted" and "Access keys" in res.final_message


def test_options_are_checked_before_connecting(azure):
    fake = azure({})
    for bad in ({"containerName": None}, {"blobPath": None}, {"blobPath": "sales/"}, {"connectionString": ""}):
        res = run_block(HERE, None, {**opts("x.csv"), **bad})
        assert res.status == "aborted", bad
    assert fake.requests == [] and fake.connection_strings == []
    # a new block no longer arrives pointed at a container called "test"
    res = run_block(HERE, None, {"connectionString": CONN})
    assert res.status == "aborted" and "container name" in res.final_message


def test_empty_blob_and_header_only_csv(azure):
    azure({("retail", "empty.csv"): b"", ("retail", "header.csv"): b"Date,Store,Units\n"})
    res = run_block(HERE, None, opts("empty.csv"))
    assert res.status == "aborted" and "is empty" in res.final_message
    out = run_block(HERE, None, opts("header.csv")).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["Date", "Store", "Units"]


def test_large_parquet(azure):
    n = 300_000
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"id": np.arange(n), "v": rng.normal(size=n), "s": rng.choice(["a", "b", "c"], n)})
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    azure({("retail", "big.parquet"): buf.getvalue()})
    t0 = time.time()
    out = run_block(HERE, None, opts("big.parquet")).raise_for_error().output(0)
    assert time.time() - t0 < 30 and len(out) == n
