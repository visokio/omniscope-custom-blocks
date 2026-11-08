#!/usr/bin/env python
"""Google BigQuery Export: loads the input records into a BigQuery table, appending to it or replacing it."""
import os
import re

import pandas as pd
from google.cloud import bigquery
from omniscope.api import OmniscopeApi

# Column names BigQuery reserves: a name may not start with these (compared case-insensitively)
RESERVED_PREFIXES = ("_TABLE_", "_FILE_", "_PARTITION", "_ROW_TIMESTAMP", "__ROOT__", "_COLIDENTIFIER")

omniscope_api = OmniscopeApi()


def text_option(name):
    value = omniscope_api.get_option(name)
    return value.strip() if isinstance(value, str) else ""


def make_client(key_file):
    """A key file, when given, is used for this block only; otherwise the server's own Google credentials."""
    if key_file:
        if not os.path.isfile(key_file):
            omniscope_api.abort(f"The JSON key file {key_file!r} was not found on the server.")
        return bigquery.Client.from_service_account_json(key_file)
    return bigquery.Client()


def column_name(field_name):
    """Letters, digits and underscores, starting with a letter or underscore, at most 300 characters."""
    name = re.sub("[^0-9a-zA-Z_]", "_", str(field_name))
    if not re.match("[a-zA-Z_]", name):
        name = "_" + name
    if name.upper().startswith(RESERVED_PREFIXES):
        name = "f" + name
    return name[:300]


def column_names(field_names):
    """BigQuery column names are case-insensitive, so names that only differ in case or punctuation
    ("Unit price", "Unit_Price") get a number: Unit_price, Unit_Price_2."""
    names, seen = [], set()
    for field in field_names:
        base = column_name(field)
        name, n = base, 1
        while name.lower() in seen:
            n += 1
            suffix = f"_{n}"
            name = base[:300 - len(suffix)] + suffix
        seen.add(name.lower())
        names.append(name)
    return names


def first_line(exc):
    text = str(exc).strip()
    return (text.splitlines() or [type(exc).__name__])[0][:500]


key_file = text_option("ApplicationCredentials")
table_id = text_option("TableId").replace(":", ".", 1)  # also accept the legacy project:dataset.table form
append_data = bool(omniscope_api.get_option("AppendData"))
data = omniscope_api.read_input_records(input_number=0)

if data is None:
    omniscope_api.abort("Connect the records to load to the block's input.")
if not table_id:
    omniscope_api.abort("Enter the table ID, for example my-project.sales.orders.")
if len(data.columns) == 0:
    omniscope_api.abort("The input has no fields.")

renamed = dict(zip(data.columns, column_names(data.columns)))
data = data.rename(columns=renamed)
changed = [f"{old} -> {new}" for old, new in renamed.items() if old != new]
if changed:
    more = " ..." if len(changed) > 20 else ""
    omniscope_api.update_message("Renamed for BigQuery: " + ", ".join(changed[:20]) + more)

try:
    client = make_client(key_file)
except Exception as exc:  # no credentials on the server, or a file that isn't a service account key
    omniscope_api.abort(f"Could not sign in to Google Cloud: {first_line(exc)}. Choose a service account's JSON key "
                        "file, or set up credentials on the server.")

disposition = bigquery.WriteDisposition.WRITE_APPEND if append_data else bigquery.WriteDisposition.WRITE_TRUNCATE
# The table is created if it doesn't exist; its schema comes from the input's field types
job_config = bigquery.LoadJobConfig(write_disposition=disposition)
try:
    omniscope_api.update_message(f"Loading {len(data)} records into {table_id}")
    job = client.load_table_from_dataframe(data, destination=table_id, job_config=job_config)
    job.result()
except Exception as exc:  # google.api_core errors: not found, permissions, schema mismatch...
    errors = getattr(exc, "errors", None) or []
    detail = "; ".join(e.get("message", "") for e in errors[:3] if isinstance(e, dict))
    omniscope_api.abort(f"BigQuery: {first_line(exc)}" + (f" ({detail})" if detail and detail not in str(exc) else ""))

loaded = getattr(job, "output_rows", None)
action = "Appended" if append_data else "Replaced the table with"
omniscope_api.close(f"{action} {loaded if loaded is not None else len(data)} records in {table_id}")
