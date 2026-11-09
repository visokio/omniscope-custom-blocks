#!/usr/bin/env python
"""Google BigQuery Import Table: reads a whole BigQuery table (or view) page by page."""
import base64
import json
import math
import os

import pandas as pd
from google.cloud import bigquery
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def text_option(name):
    value = omniscope_api.get_option(name)
    return value.strip() if isinstance(value, str) else ""


def make_client(key_file, project):
    """A key file, when given, is used for this block only; otherwise the server's own Google credentials."""
    if key_file:
        if not os.path.isfile(key_file):
            omniscope_api.abort(f"The JSON key file {key_file!r} was not found on the server.")
        return bigquery.Client.from_service_account_json(key_file, project=project or None)
    return bigquery.Client(project=project or None)


def missing(value):
    return value is None or value is pd.NA or value is pd.NaT or (isinstance(value, float) and math.isnan(value))


def json_text(value):
    if missing(value):
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))


def to_omniscope(df, schema):
    """Give each BigQuery type an Omniscope field type, from the result's schema (not from the values, so every
    run gives the same types): NUMERIC to Decimal, DATE to Date, TIME to text, arrays/STRUCT/JSON to JSON text,
    BYTES to base64 text, GEOGRAPHY to WKT text."""
    types = {f.name: ((f.field_type or "").upper(), (f.mode or "").upper()) for f in schema}
    for col in df.columns:
        ftype, mode = types.get(col, ("", ""))
        s = df[col]
        if mode == "REPEATED" or ftype in ("RECORD", "STRUCT", "JSON", "RANGE"):
            s = s.astype(object).map(json_text)
        elif ftype in ("NUMERIC", "BIGNUMERIC", "DECIMAL", "BIGDECIMAL"):
            s = s.astype(object).map(lambda v: math.nan if missing(v) else float(v)).astype("float64")
        elif ftype == "DATE":
            s = pd.to_datetime(s.astype(object).map(lambda v: None if missing(v) else str(v)), errors="coerce")
        elif ftype == "TIME":
            s = s.astype(object).map(lambda v: None if missing(v) else str(v))
        elif ftype == "BYTES":
            s = s.astype(object).map(lambda v: None if missing(v) else base64.b64encode(bytes(v)).decode("ascii"))
        elif ftype == "GEOGRAPHY":
            s = s.astype(object).map(lambda v: None if missing(v) else str(v))
        df[col] = s
    return df


def first_line(exc):
    text = str(exc).strip()
    return (text.splitlines() or [type(exc).__name__])[0][:500]


key_file = text_option("ApplicationCredentials")
table_id = text_option("TableId").replace(":", ".", 1)  # also accept the legacy project:dataset.table form
page_size = omniscope_api.get_option("PageSize")
max_rows = omniscope_api.get_option("MaxRows")
if not table_id:
    omniscope_api.abort("Enter the table ID, for example my-project.sales.orders.")
page_size = int(page_size) if page_size else 10_000
max_rows = int(max_rows) if max_rows else None
if page_size < 1 or (max_rows is not None and max_rows < 0):
    omniscope_api.abort("Page size must be at least 1, and the maximum number of records at least 0.")

try:
    client = make_client(key_file, None)
except Exception as exc:  # no credentials on the server, or a file that isn't a service account key
    omniscope_api.abort(f"Could not sign in to Google Cloud: {first_line(exc)}. Choose a service account's JSON key "
                        "file, or set up credentials on the server.")

written = 0
try:
    table = client.get_table(table_id)
    if (table.table_type or "TABLE").upper() in ("TABLE", "SNAPSHOT"):
        rows = client.list_rows(table, page_size=page_size, max_results=max_rows)
    else:
        # Views, materialised views and external tables can't be listed row by row: query them instead
        limit = f" LIMIT {max_rows}" if max_rows is not None else ""
        ref = table.reference
        sql = f"SELECT * FROM `{ref.project}.{ref.dataset_id}.{ref.table_id}`{limit}"
        rows = client.query(sql).result(page_size=page_size)
    schema = list(rows.schema or table.schema or [])
    for chunk in rows.to_dataframe_iterable():
        if len(chunk) == 0:
            continue
        omniscope_api.write_output_records(to_omniscope(chunk, schema), output_number=0)
        written += len(chunk)
        omniscope_api.update_message(f"{written} records read")
except Exception as exc:  # google.api_core errors: not found, permissions, quota...
    omniscope_api.abort(f"BigQuery: {first_line(exc)}")

if written == 0:
    # An empty table still gives its fields, so the blocks after this one can be set up
    empty = pd.DataFrame({f.name: pd.Series([], dtype=object) for f in schema})
    omniscope_api.write_output_records(to_omniscope(empty, schema), output_number=0)
omniscope_api.close(f"{written} records from {table_id}")
