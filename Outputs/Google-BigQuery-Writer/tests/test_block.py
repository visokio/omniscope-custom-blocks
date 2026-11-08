"""Google BigQuery Export block tests. No call reaches Google: a stand-in `google.cloud.bigquery` module records the
load the block would send (the records, the destination table and the write disposition) and answers as BigQuery
would."""
import datetime
import json
import os
import sys
import time
import types
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "store-daily-totals.csv")
TABLE = "example-project.retail.store_daily_totals"


class SchemaField:
    def __init__(self, name, field_type, mode="NULLABLE"):
        self.name, self.field_type, self.mode = name, field_type, mode


def frame_from_canned(payload):
    """Turn a canned result ({"schema": [[name, type, mode]], "rows": [[...]]}) into the DataFrame
    google-cloud-bigquery's to_dataframe() gives: INT64 as Int64, NUMERIC as Decimal, DATE as datetime.date,
    TIMESTAMP as UTC datetimes, STRUCT as dict, REPEATED as a list."""
    schema = [SchemaField(*f) for f in payload["schema"]]
    cols = {}
    for i, f in enumerate(schema):
        values = [r[i] for r in payload["rows"]]
        t = f.field_type
        if f.mode == "REPEATED" or t in ("RECORD", "STRUCT", "JSON", "BYTES", "TIME", "GEOGRAPHY", "STRING"):
            if t == "BYTES":
                values = [None if v is None else v.encode() for v in values]
            if t == "TIME":
                values = [None if v is None else datetime.time.fromisoformat(v) for v in values]
            s = pd.Series(values, dtype=object)
        elif t in ("NUMERIC", "BIGNUMERIC"):
            s = pd.Series([None if v is None else Decimal(str(v)) for v in values], dtype=object)
        elif t == "DATE":
            s = pd.Series([None if v is None else datetime.date.fromisoformat(v) for v in values], dtype=object)
        elif t == "TIMESTAMP":
            s = pd.to_datetime(pd.Series(values), utc=True)
        elif t in ("INT64", "INTEGER"):
            s = pd.Series(values, dtype="Int64")
        elif t in ("BOOL", "BOOLEAN"):
            s = pd.Series(values, dtype="boolean")
        else:
            s = pd.Series(values, dtype="float64")
        cols[f.name] = s
    return schema, pd.DataFrame(cols, columns=[f.name for f in schema])


class RowIterator:
    def __init__(self, schema, frame, page_size=None, max_results=None):
        self.schema = schema
        self.frame = frame if max_results is None else frame.head(max_results)
        self.page_size = page_size or 50

    def to_dataframe(self):
        return self.frame.copy()

    def to_dataframe_iterable(self):
        if len(self.frame) == 0:
            yield self.frame.copy()  # BigQuery gives one empty page for an empty table
        for start in range(0, len(self.frame), self.page_size):
            yield self.frame.iloc[start:start + self.page_size].reset_index(drop=True)


class QueryJob:
    def __init__(self, rows, error=None, affected=None):
        self.rows, self.error, self.num_dml_affected_rows = rows, error, affected

    def result(self, page_size=None):
        if self.error:
            raise self.error
        if page_size:
            self.rows.page_size = page_size
        return self.rows


class FakeBigQuery:
    """Stands in for google.cloud.bigquery and records every call."""

    def __init__(self):
        self.calls = []
        self.queries = {}    # sql -> QueryJob
        self.tables = {}     # "project.dataset.table" -> (table_type, schema, frame)
        self.load_error = None
        fake = self

        class WriteDisposition:
            WRITE_APPEND = "WRITE_APPEND"
            WRITE_TRUNCATE = "WRITE_TRUNCATE"

        class LoadJobConfig:
            def __init__(self, **kw):
                self.__dict__.update(kw)

        class Ref:
            def __init__(self, full):
                self.project, self.dataset_id, self.table_id = full.split(".")

        class Table:
            def __init__(self, full, table_type, schema):
                self.reference, self.table_type, self.schema = Ref(full), table_type, schema

        class LoadJob:
            def __init__(self, n):
                self.output_rows = n

            def result(self):
                return self

        class Client:
            def __init__(self, project=None, _key=None):
                # Like google.auth: a GOOGLE_APPLICATION_CREDENTIALS that is set must name a file
                env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
                if _key is None and env is not None and not os.path.isfile(env):
                    raise FakeBigQuery.DefaultCredentialsError(f"File {env} was not found.")
                self.project = project or "key-project"
                fake.calls.append(("client", project, _key))

            @classmethod
            def from_service_account_json(cls, path, project=None):
                return cls(project=project, _key=path)

            def query(self, sql):
                fake.calls.append(("query", sql))
                if sql not in fake.queries:
                    raise FakeBigQuery.BadRequest(f"400 Syntax error: Unexpected identifier at [1:1]\n\nLocation: EU")
                return fake.queries[sql]

            def get_table(self, table_id):
                fake.calls.append(("get_table", table_id))
                full = table_id if table_id.count(".") == 2 else f"{self.project}.{table_id}"
                if full not in fake.tables:
                    raise FakeBigQuery.NotFound(f"404 Not found: Table {full} was not found in location EU")
                table_type, schema, _ = fake.tables[full]
                return Table(full, table_type, schema)

            def list_rows(self, table, page_size=None, max_results=None):
                ref = table.reference
                full = f"{ref.project}.{ref.dataset_id}.{ref.table_id}"
                fake.calls.append(("list_rows", full, page_size, max_results))
                if table.table_type != "TABLE":
                    raise FakeBigQuery.BadRequest(f"400 Cannot list a table of type {table.table_type}.")
                _, schema, frame = fake.tables[full]
                return RowIterator(schema, frame, page_size, max_results)

            def load_table_from_dataframe(self, df, destination, job_config=None):
                fake.calls.append(("load", df.copy(), destination, job_config.write_disposition))
                lower = [str(c).lower() for c in df.columns]
                if len(set(lower)) != len(lower):
                    raise FakeBigQuery.BadRequest("400 Duplicate column names in the input: " + ", ".join(df.columns))
                if fake.load_error:
                    raise fake.load_error
                return LoadJob(len(df))

        self.module = types.ModuleType("google.cloud.bigquery")
        self.module.Client = Client
        self.module.WriteDisposition = WriteDisposition
        self.module.LoadJobConfig = LoadJobConfig
        self.module.SchemaField = SchemaField

    class BadRequest(Exception):
        pass

    class NotFound(Exception):
        pass

    class DefaultCredentialsError(Exception):
        pass


@pytest.fixture
def bq(monkeypatch):
    """Install a FakeBigQuery as google.cloud.bigquery for the script to import."""
    fake = FakeBigQuery()
    google, cloud = types.ModuleType("google"), types.ModuleType("google.cloud")
    google.cloud, cloud.bigquery = cloud, fake.module
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", fake.module)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    return fake


def loads(bq):
    return [c for c in bq.calls if c[0] == "load"]


def test_loads_the_sample_with_bigquery_column_names(bq):
    res = run_block(HERE, SAMPLE, {"TableId": TABLE}).raise_for_error()
    (_, df, dest, disposition), = loads(bq)
    assert dest == TABLE and disposition == "WRITE_APPEND" and len(df) == 20
    assert list(df.columns) == ["Store", "Sale_date", "Units_sold", "Revenue____", "Click___collect__"]
    assert pd.api.types.is_datetime64_any_dtype(df["Sale_date"]) and str(df["Units_sold"].dtype) == "Int64"
    assert res.final_message == f"Appended 20 records in {TABLE}"
    assert any("Renamed for BigQuery: Sale date -> Sale_date" in m for m in res.messages)


def test_replace_the_table(bq):
    res = run_block(HERE, SAMPLE, {"TableId": TABLE, "AppendData": False}).raise_for_error()
    assert loads(bq)[0][3] == "WRITE_TRUNCATE" and res.final_message.startswith("Replaced the table with 20")


def test_names_that_clash_get_a_number(bq):
    # The original stopped with "Unable to detemine a map" for "Unit price"/"Unit_price", and sent
    # "Region"/"region" on to BigQuery, which refuses columns that differ only in case
    df = pd.DataFrame({"Unit price": [1.5], "Unit_price": [2.5], "Region": ["N"], "region": ["S"],
                       "2026 target": [10], "_PARTITIONTIME": [1], "Ünits": [3]})
    run_block(HERE, df, {"TableId": TABLE}).raise_for_error()
    cols = list(loads(bq)[0][1].columns)
    assert cols == ["Unit_price", "Unit_price_2", "Region", "region_2", "_2026_target", "f_PARTITIONTIME", "_nits"]


def test_cleared_key_file_uses_the_server_credentials(bq, tmp_path):
    # The original set GOOGLE_APPLICATION_CREDENTIALS to "" for an emptied key file, so signing in failed
    run_block(HERE, SAMPLE, {"TableId": TABLE, "ApplicationCredentials": ""}).raise_for_error()
    assert bq.calls[0] == ("client", None, None)
    key = tmp_path / "key.json"
    key.write_text("{}")
    run_block(HERE, SAMPLE, {"TableId": TABLE, "ApplicationCredentials": str(key)}).raise_for_error()
    assert ("client", None, str(key)) in bq.calls and "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ


def test_empty_input_loads_no_records(bq):
    df = pd.read_csv(SAMPLE).head(0)
    res = run_block(HERE, df, {"TableId": TABLE}).raise_for_error()
    assert len(loads(bq)[0][1]) == 0 and "0 records" in res.final_message


def test_problems_abort_with_a_message(bq):
    # The original crashed on an unconnected input and showed BigQuery's errors as a traceback
    res = run_block(HERE, None, {"TableId": TABLE})
    assert res.status == "aborted" and "Connect" in res.final_message and not loads(bq)
    res = run_block(HERE, SAMPLE, {"TableId": ""})
    assert res.status == "aborted" and "table ID" in res.final_message
    bq.load_error = FakeBigQuery.BadRequest("400 Provided Schema does not match Table. Field Units_sold has changed "
                                            "type from STRING to INTEGER")
    res = run_block(HERE, SAMPLE, {"TableId": TABLE})
    assert res.status == "aborted" and "Provided Schema does not match" in res.final_message


def test_wrong_types_are_sent_as_they_are(bq):
    # Mixed or odd field types reach BigQuery as the input has them; text stays text
    df = pd.DataFrame({"code": ["001", "A2", None], "flag": [True, False, True], "n": [1, None, 3]})
    run_block(HERE, df, {"TableId": TABLE}).raise_for_error()
    sent = loads(bq)[0][1]
    assert sent["code"].tolist()[:2] == ["001", "A2"] and sent["flag"].dtype == bool and str(sent["n"].dtype) == "Int64"


def test_large_input(bq):
    n = 300_000
    df = pd.DataFrame({"id": np.arange(n), "v": np.random.default_rng(2).normal(size=n), "s": ["x"] * n})
    t0 = time.time()
    res = run_block(HERE, df, {"TableId": TABLE}).raise_for_error()
    assert time.time() - t0 < 30 and len(loads(bq)[0][1]) == n and f"{n} records" in res.final_message
