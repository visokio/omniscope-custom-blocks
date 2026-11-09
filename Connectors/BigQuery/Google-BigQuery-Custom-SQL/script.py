#!/usr/bin/env python
"""Google BigQuery Custom SQL: runs a query (GoogleSQL) on BigQuery and outputs its result."""
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
project = text_option("ProjectId")
query = text_option("Query")
if not query:
    omniscope_api.abort("Enter the SQL query to run.")

try:
    client = make_client(key_file, project)
except Exception as exc:  # no credentials on the server, or a file that isn't a service account key
    omniscope_api.abort(f"Could not sign in to Google Cloud: {first_line(exc)}. Choose a service account's JSON key "
                        "file, or set up credentials on the server.")
try:
    omniscope_api.update_message("Running the query")
    job = client.query(query)
    rows = job.result()
    data = rows.to_dataframe()
except Exception as exc:  # google.api_core errors: bad SQL, permissions, quota...
    omniscope_api.abort(f"BigQuery: {first_line(exc)}")

schema = list(rows.schema or [])
if not schema:
    # A statement such as INSERT, UPDATE, CREATE TABLE or a script returns no table
    affected = getattr(job, "num_dml_affected_rows", None)
    omniscope_api.close("The statement ran but returned no table"
                        + (f" ({affected} rows affected)" if affected is not None else ""))
else:
    data = to_omniscope(data, schema)
    omniscope_api.write_output_records(data, output_number=0)
    omniscope_api.close(f"{len(data)} records")
