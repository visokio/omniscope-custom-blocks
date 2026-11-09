"""Google BigQuery Import Table block tests. No call reaches Google: a stand-in `google.cloud.bigquery` module answers
from the canned table saved beside this file (orders-table.json) and records each call."""
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
TESTS = os.path.join(HERE, "tests")
PLACEHOLDER = os.path.join(HERE, "sample-data", "placeholder.csv")
TABLE = "example-project.retail.orders"


def canned(name):
    with open(os.path.join(TESTS, name), encoding="utf-8") as fh:
        return json.load(fh)


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


def add_table(bq, table_type="TABLE", rows=None):
    payload = canned("orders-table.json")
    if rows is not None:
        payload["rows"] = rows
    schema, frame = frame_from_canned(payload)
    bq.tables[TABLE] = (table_type, schema, frame)
    return schema, frame


def test_reads_the_table_page_by_page(bq):
    add_table(bq)
    res = run_block(HERE, None, {"TableId": TABLE, "PageSize": 15}).raise_for_error()
    out = res.output(0)
    assert len(out) == 40 and out["order_id"].tolist() == list(range(1001, 1041))
    assert ("list_rows", TABLE, 15, None) in bq.calls
    assert out["amount"].dtype == "float64" and pd.api.types.is_datetime64_any_dtype(out["order_date"])
    assert str(out["ordered_at"].dt.tz) == "UTC"
    assert res.messages[-1] == "40 records read"


def test_matches_the_placeholder_sample(bq):
    add_table(bq)
    out = run_block(HERE, None, {"TableId": TABLE}).raise_for_error().output(0)
    got = pd.read_csv(pd.io.common.StringIO(out.to_csv(index=False)))
    pd.testing.assert_frame_equal(got, pd.read_csv(PLACEHOLDER))


def test_every_page_has_the_same_types(bq):
    # A page whose NUMERIC values are all missing must still give a decimal field
    rows = canned("orders-table.json")["rows"]
    for r in rows[10:20]:
        r[6] = None
    add_table(bq, rows=rows)
    out = run_block(HERE, None, {"TableId": TABLE, "PageSize": 10}).raise_for_error().output(0)
    assert out["amount"].dtype == "float64" and out["amount"].isna().sum() == 10


def test_views_are_read_with_a_query(bq):
    # The original listed rows directly, which BigQuery refuses for a view
    schema, frame = add_table(bq, "VIEW")
    sql = f"SELECT * FROM `{TABLE}` LIMIT 5"
    bq.queries[sql] = QueryJob(RowIterator(schema, frame.head(5)))
    out = run_block(HERE, None, {"TableId": TABLE, "MaxRows": 5}).raise_for_error().output(0)
    assert len(out) == 5 and ("query", sql) in bq.calls


def test_maximum_records_and_legacy_ids(bq):
    add_table(bq)
    out = run_block(HERE, None, {"TableId": "example-project:retail.orders", "MaxRows": 12}).raise_for_error().output(0)
    assert len(out) == 12 and ("get_table", TABLE) in bq.calls and ("list_rows", TABLE, 10000, 12) in bq.calls


def test_empty_table_keeps_its_fields(bq):
    # The original wrote nothing for an empty table
    add_table(bq, rows=[])
    res = run_block(HERE, None, {"TableId": TABLE}).raise_for_error()
    out = res.output(0)
    assert len(out) == 0 and list(out.columns)[:3] == ["order_id", "order_date", "ordered_at"]
    assert pd.api.types.is_datetime64_any_dtype(out["order_date"]) and out["amount"].dtype == "float64"


def test_cleared_key_file_uses_the_server_credentials(bq):
    # The original set GOOGLE_APPLICATION_CREDENTIALS to "" for an emptied key file, so signing in failed
    add_table(bq)
    run_block(HERE, None, {"TableId": TABLE, "ApplicationCredentials": ""}).raise_for_error()
    assert bq.calls[0] == ("client", None, None)


def test_errors_and_bad_options_abort_with_a_message(bq, tmp_path):
    res = run_block(HERE, None, {"TableId": "example-project.retail.missing"})
    assert res.status == "aborted" and res.final_message.startswith("BigQuery: 404 Not found")
    res = run_block(HERE, None, {"TableId": None})
    assert res.status == "aborted" and "table ID" in res.final_message
    res = run_block(HERE, None, {"TableId": TABLE, "ApplicationCredentials": str(tmp_path / "gone.json")})
    assert res.status == "aborted" and "was not found" in res.final_message
    res = run_block(HERE, None, {"TableId": TABLE, "MaxRows": -1})
    assert res.status == "aborted"


def test_large_table(bq):
    n = 250_000
    payload = {"schema": [["id", "INT64"], ["v", "FLOAT64"], ["day", "DATE"]],
               "rows": [[i, i / 3, "2026-01-31"] for i in range(n)]}
    schema, frame = frame_from_canned(payload)
    bq.tables["p.d.big"] = ("TABLE", schema, frame)
    t0 = time.time()
    out = run_block(HERE, None, {"TableId": "p.d.big", "PageSize": 25_000}).raise_for_error().output(0)
    assert time.time() - t0 < 30 and len(out) == n and out["id"].iloc[-1] == n - 1
