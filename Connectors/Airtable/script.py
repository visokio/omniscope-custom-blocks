"""Airtable: reads every record of an Airtable table (or one of its views) through the Airtable REST API."""
import json
import time
import urllib.parse

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

API_URL = "https://api.airtable.com/v0"
TIMEOUT = 60          # seconds to wait for one page
RATE_LIMIT_WAIT = 30  # Airtable asks clients to wait 30 seconds after a 429 (too many requests)
MAX_RETRIES = 4

omniscope_api = OmniscopeApi()


def text_option(name):
    value = omniscope_api.get_option(name)
    return value.strip() if isinstance(value, str) else ""


token = text_option("token")
base_id = text_option("base_id")
table = text_option("table")
view = text_option("view")
formula = text_option("filter_formula")
page_size = omniscope_api.get_option("page_size")

if not token or not base_id or not table:
    omniscope_api.abort("Enter a personal access token, a base ID and a table name or ID.")
try:
    page_size = 100 if page_size is None else int(page_size)
except (TypeError, ValueError):
    page_size = 0
if not 1 <= page_size <= 100:
    omniscope_api.abort("Page size must be a whole number from 1 to 100.")

# Table names may contain spaces, slashes and other characters that must be escaped in the URL path
url = f"{API_URL}/{urllib.parse.quote(base_id, safe='')}/{urllib.parse.quote(table, safe='')}"
headers = {"Authorization": f"Bearer {token}"}
params = {"pageSize": page_size}
if view:
    params["view"] = view
if formula:
    params["filterByFormula"] = formula


def error_text(response):
    """Airtable's error body is {"error": {"type": ..., "message": ...}} or {"error": "NOT_FOUND"}."""
    try:
        err = response.json().get("error")
    except ValueError:
        return response.text[:300]
    if isinstance(err, dict):
        return ": ".join(str(err[k]) for k in ("type", "message") if err.get(k))
    return str(err)


HINTS = {
    401: " Check the personal access token.",
    403: " Check that the token has the data.records:read scope and access to this base.",
    404: " Check the base ID, the table name or ID and the view.",
    422: " Check the view name and the filter formula.",
}


def get_page():
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            omniscope_api.abort(f"Could not reach Airtable: {exc}")
        if response.status_code == 429 and attempt < MAX_RETRIES:
            omniscope_api.update_message(f"Airtable rate limit reached; waiting {RATE_LIMIT_WAIT} seconds")
            time.sleep(RATE_LIMIT_WAIT)
            continue
        if response.status_code != 200:
            omniscope_api.abort(f"Airtable returned {response.status_code}: {error_text(response)}."
                                + HINTS.get(response.status_code, ""))
        return response.json()


records = []
while True:
    data = get_page()
    for rec in data.get("records", []):
        records.append((rec.get("id"), rec.get("fields") or {}))
    omniscope_api.update_message(f"{len(records)} records read")
    offset = data.get("offset")
    if not offset:
        break
    params["offset"] = offset

# The record ID comes first. If the table has its own field called "id", that field keeps the name.
field_names = {name for _, fields in records for name in fields}
id_field = "Airtable record ID" if "id" in field_names else "id"
rows = [{id_field: rec_id, **fields} for rec_id, fields in records]
df = pd.DataFrame(rows) if rows else pd.DataFrame({id_field: pd.Series([], dtype=object)})


def serialise(value):
    """Lists and objects (attachments, linked records, collaborators...) become JSON text."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


for col in df.columns:
    if not pd.api.types.is_object_dtype(df[col].dtype) and not pd.api.types.is_string_dtype(df[col].dtype):
        continue
    s = df[col].map(serialise)
    present = s.dropna()
    if len(present) and present.map(lambda v: isinstance(v, bool)).all():
        # Airtable leaves unticked checkboxes out of a record, so missing means unticked
        s = s.where(s.notna(), False).astype(bool)
    elif present.map(lambda v: isinstance(v, str)).any() and not present.map(lambda v: isinstance(v, str)).all():
        # A field mixing text and numbers (a formula that sometimes errors, for example) becomes text
        s = s.map(lambda v: v if v is None or (isinstance(v, float) and pd.isna(v)) else str(v))
    df[col] = s

omniscope_api.write_output_records(df, 0)
omniscope_api.close(f"{len(df)} records" if len(df) else "The table (or view, or filter) has no records")
