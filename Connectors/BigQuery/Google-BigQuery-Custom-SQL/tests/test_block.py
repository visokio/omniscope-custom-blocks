"""Google BigQuery Custom SQL block tests. No call reaches Google: a stand-in `google.cloud.bigquery` module answers
from the canned results saved beside this file (query-result.json, all-types.json) and records each call."""
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


def sample(bq):
    payload = canned("query-result.json")
    schema, frame = frame_from_canned(payload)
    bq.queries[payload["sql"]] = QueryJob(RowIterator(schema, frame))
    return payload["sql"]


def test_runs_the_query_and_maps_types(bq):
    sql = sample(bq)
    res = run_block(HERE, None, {"Query": sql}).raise_for_error()
    out = res.output(0)
    assert len(out) == 18
    assert list(out.columns) == ["region", "month", "orders", "revenue", "avg_basket", "top_products"]
    assert ("query", sql) in bq.calls and bq.calls[0] == ("client", None, None)  # the server's own credentials
    # NUMERIC to decimal numbers, DATE to dates, arrays to JSON text (the original passed Decimal and
    # datetime.date objects and arrays straight through)
    assert out["revenue"].dtype == "float64" and out["avg_basket"].dtype == "float64"
    assert pd.api.types.is_datetime64_any_dtype(out["month"])
    assert out["top_products"].iloc[0] == '["Oat flapjack", "Ginger beer"]'
    assert str(out["orders"].dtype) == "Int64" and out["orders"].sum() == 7146
    assert res.final_message == "18 records"


def test_matches_the_placeholder_sample(bq):
    out = run_block(HERE, None, {"Query": sample(bq)}).raise_for_error().output(0)
    got = pd.read_csv(pd.io.common.StringIO(out.to_csv(index=False)))
    pd.testing.assert_frame_equal(got, pd.read_csv(PLACEHOLDER))


def test_every_bigquery_type(bq):
    schema, frame = frame_from_canned(canned("all-types.json"))
    bq.queries["SELECT * FROM t"] = QueryJob(RowIterator(schema, frame))
    out = run_block(HERE, None, {"Query": "SELECT * FROM t"}).raise_for_error().output(0)
    first, empty = out.iloc[0], out.iloc[1]
    assert first["amount"] == 12.345 and pd.isna(empty["amount"])
    assert first["day"] == pd.Timestamp("2026-03-02") and pd.isna(empty["day"])
    assert first["opens"] == "09:00:00" and first["paid"] == True  # noqa: E712
    assert first["tags"] == '["a", "b"]' and empty["tags"] == "[]"
    assert json.loads(first["address"]) == {"town": "Leeds", "postcode": "LS1"} and pd.isna(empty["address"])
    assert first["extra"] == '{"k": 1}' and first["blob"] == "aGk=" and first["where"] == "POINT(-1.55 53.8)"


def test_bigquery_date_type(bq):
    # With the db-dtypes package (a dependency), DATE columns arrive as the "dbdate" type
    db_dtypes = pytest.importorskip("db_dtypes")
    schema, frame = frame_from_canned(canned("all-types.json"))
    frame["day"] = frame["day"].astype("dbdate")
    bq.queries["q"] = QueryJob(RowIterator(schema, frame))
    out = run_block(HERE, None, {"Query": "q"}).raise_for_error().output(0)
    assert pd.api.types.is_datetime64_any_dtype(out["day"]) and out["day"].iloc[0] == pd.Timestamp("2026-03-02")


def test_project_and_key_file(bq, tmp_path):
    key = tmp_path / "key.json"
    key.write_text("{}")
    sql = sample(bq)
    run_block(HERE, None, {"Query": sql, "ApplicationCredentials": str(key), "ProjectId": "billing-project"})
    assert bq.calls[0] == ("client", "billing-project", str(key))
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ  # the key is used for this block only
    res = run_block(HERE, None, {"Query": sql, "ApplicationCredentials": str(tmp_path / "gone.json")})
    assert res.status == "aborted" and "was not found" in res.final_message


def test_cleared_key_file_uses_the_server_credentials(bq):
    # The original set GOOGLE_APPLICATION_CREDENTIALS to "" for an emptied key file, so signing in failed
    sql = sample(bq)
    run_block(HERE, None, {"Query": sql, "ApplicationCredentials": ""}).raise_for_error()
    assert bq.calls[0] == ("client", None, None)


def test_no_table_from_a_statement(bq):
    bq.queries["DELETE FROM t WHERE x"] = QueryJob(RowIterator([], pd.DataFrame()), affected=4)
    res = run_block(HERE, None, {"Query": "DELETE FROM t WHERE x"}).raise_for_error()
    assert res.output(0) is None and "4 rows affected" in res.final_message


def test_empty_result_keeps_its_fields(bq):
    payload = canned("query-result.json")
    schema, frame = frame_from_canned({**payload, "rows": []})
    bq.queries["q"] = QueryJob(RowIterator(schema, frame))
    out = run_block(HERE, None, {"Query": "q"}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns)[:2] == ["region", "month"]


def test_errors_abort_with_bigquerys_message(bq, monkeypatch):
    # The original called cancel() and then re-raised, so the block showed as cancelled, with a traceback
    res = run_block(HERE, None, {"Query": "SELEC 1"})
    assert res.status == "aborted" and res.final_message == "BigQuery: 400 Syntax error: Unexpected identifier at [1:1]"
    res = run_block(HERE, None, {"Query": "  "})
    assert res.status == "aborted" and "Enter the SQL query" in res.final_message
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/nowhere/key.json")
    res = run_block(HERE, None, {"Query": "q"})
    assert res.status == "aborted" and "Could not sign in" in res.final_message


def test_large_result(bq):
    n = 200_000
    rng = np.random.default_rng(3)
    payload = {"schema": [["id", "INT64"], ["amount", "NUMERIC"], ["day", "DATE"]],
               "rows": [[i, round(float(v), 2), "2026-03-01"] for i, v in enumerate(rng.uniform(0, 100, n))]}
    schema, frame = frame_from_canned(payload)
    bq.queries["big"] = QueryJob(RowIterator(schema, frame))
    t0 = time.time()
    out = run_block(HERE, None, {"Query": "big"}).raise_for_error().output(0)
    assert time.time() - t0 < 30 and len(out) == n and out["amount"].dtype == "float64"
