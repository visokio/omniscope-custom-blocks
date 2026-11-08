"""Dune connector: the result of a saved Dune query, either its latest stored result or a fresh execution,
from the Dune API (https://docs.dune.com/api-reference). Every page of the result is read and the columns
are typed from Dune's column types."""
import json
import re
import time

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

BASE_URL = "https://api.dune.com/api/v1"
TIMEOUT = 120
PAGE_LIMIT = 25000   # rows asked for per page; Dune may lower it and says where the next page starts
POLL_SECONDS = 5
FINISHED = "QUERY_STATE_COMPLETED"
PARTIAL = "QUERY_STATE_COMPLETED_PARTIAL"
FAILED = {"QUERY_STATE_FAILED", "QUERY_STATE_CANCELED", "QUERY_STATE_CANCELLED", "QUERY_STATE_EXPIRED"}
EXECUTION_COLUMNS = ["Execution ID", "Query ID", "State", "Submitted", "Started", "Ended", "Expires", "Rows"]


def option_text(name):
    value = omniscope_api.get_option(name)
    return "" if value is None else str(value).strip()


class DuneError(Exception):
    pass


class DuneAPI:
    def __init__(self, api_key):
        self.session = requests.Session()
        self.session.headers.update({"X-Dune-Api-Key": api_key})

    def call(self, method, url, **kw):
        try:
            r = self.session.request(method, url, timeout=TIMEOUT, **kw)
        except requests.RequestException as e:
            raise DuneError(f"Could not reach Dune: {type(e).__name__}")
        if r.status_code != 200:
            try:
                reason = r.json().get("error") or ""
            except ValueError:
                reason = ""
            reason = reason if isinstance(reason, str) else json.dumps(reason)
            raise DuneError(f"Dune refused the request (HTTP {r.status_code})" + (f": {reason}" if reason else "."),
                            r.status_code)
        try:
            return r.json()
        except ValueError:
            raise DuneError("Dune's answer was not JSON.")

    def execute(self, query_id, performance):
        body = self.call("POST", f"{BASE_URL}/query/{query_id}/execute", json={"performance": performance})
        if not body.get("execution_id"):
            raise DuneError("Dune did not return an execution id.")
        return body["execution_id"]

    def wait(self, execution_id):
        while True:
            status = self.call("GET", f"{BASE_URL}/execution/{execution_id}/status")
            state = status.get("state", "")
            if state in (FINISHED, PARTIAL):
                return state
            if state in FAILED:
                error = status.get("error") or {}
                detail = error.get("message") if isinstance(error, dict) else str(error)
                raise DuneError(f"The query execution ended with {state.replace('QUERY_STATE_', '').lower()}"
                                + (f": {detail}" if detail else "."))
            position = status.get("queue_position")
            omniscope_api.update_message(f"Execution {execution_id}: {state.replace('QUERY_STATE_', '').lower()}"
                                         + (f", queue position {position}" if position else ""))
            time.sleep(POLL_SECONDS)

    def results(self, url):
        """Every page of a results URL. Returns the first page's body (for the execution details) and all rows."""
        params = {"limit": PAGE_LIMIT, "allow_partial_results": "true"}
        first, rows, page = None, [], 0
        while url:
            body = self.call("GET", url, params=params)
            if first is None:
                first = body
            rows.extend((body.get("result") or {}).get("rows") or [])
            page += 1
            omniscope_api.update_message(f"Read {len(rows)} rows ({page} page(s))")
            url, params = body.get("next_uri"), None  # next_uri carries its own limit and offset
        return first, rows


def to_text(value):
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def typed_column(values, dune_type):
    t = (dune_type or "").lower()
    s = pd.Series(values, dtype=object)
    if t in ("tinyint", "smallint", "integer", "int", "bigint"):
        return pd.to_numeric(s, errors="coerce").astype("Int64")
    if t in ("double", "real", "float") or t.startswith("decimal"):
        return pd.to_numeric(s, errors="coerce").astype("float64")
    if t == "boolean":
        return s.map(lambda v: None if v is None else bool(v)).astype("boolean")
    if t == "date" or t.startswith("timestamp"):
        text = s.map(lambda v: None if v is None else re.sub(r" UTC$", "", str(v)))
        return pd.to_datetime(text, utc=True, errors="coerce", format="mixed")
    # varchar, varbinary (0x...), uint256 / int256 (too large for a number field), arrays, maps, rows
    return s.map(to_text).astype(object)


def rows_frame(rows, metadata):
    names = list(metadata.get("column_names") or [])
    for row in rows:  # columns Dune did not list (should not happen) are kept after the listed ones
        for k in row:
            if k not in names:
                names.append(k)
    types = dict(zip(metadata.get("column_names") or [], metadata.get("column_types") or []))
    data = {}
    for n in names:
        values = [row.get(n) for row in rows]
        if n in types:
            data[n] = typed_column(values, types[n])
        else:
            data[n] = pd.Series([to_text(v) for v in values], dtype=object)
    return pd.DataFrame(data, columns=names)


def stamp(value):
    if not value:
        return pd.NaT
    return pd.to_datetime(value, utc=True, errors="coerce", format="mixed")


def execution_frame(body, row_count):
    meta = (body.get("result") or {}).get("metadata") or {}
    total = meta.get("total_row_count", row_count)
    frame = pd.DataFrame([{
        "Execution ID": body.get("execution_id"), "Query ID": body.get("query_id"), "State": body.get("state"),
        "Submitted": stamp(body.get("submitted_at")), "Started": stamp(body.get("execution_started_at")),
        "Ended": stamp(body.get("execution_ended_at")), "Expires": stamp(body.get("expires_at")), "Rows": total,
    }], columns=EXECUTION_COLUMNS)
    frame["Query ID"] = pd.to_numeric(frame["Query ID"], errors="coerce").astype("Int64")
    frame["Rows"] = pd.to_numeric(frame["Rows"], errors="coerce").astype("Int64")
    for c in ("Submitted", "Started", "Ended", "Expires"):
        frame[c] = pd.to_datetime(frame[c], utc=True)
    for c in ("Execution ID", "State"):
        frame[c] = frame[c].astype(object)
    return frame


api_key = option_text("duneApiKey")
query_text = option_text("queryId")
mode = option_text("mode") or "retrieveLatest"
performance = option_text("performance") or "medium"

if not api_key:
    omniscope_api.abort("Enter your Dune API key (Settings > API on dune.com).")
# A query id, or a query's address such as https://dune.com/queries/241/388
m = re.fullmatch(r"(\d+)", query_text) or re.search(r"/queries/(\d+)", query_text)
if not m:
    omniscope_api.abort(f"Query ID must be a number, or a query's address such as "
                        f"https://dune.com/queries/241; got '{query_text}'.")
query_id = m.group(1)

dune = DuneAPI(api_key)
try:
    if mode == "execAndRetrieve":
        omniscope_api.update_message(f"Executing query {query_id} ({performance} engine)")
        execution_id = dune.execute(query_id, performance)
        dune.wait(execution_id)
        body, rows = dune.results(f"{BASE_URL}/execution/{execution_id}/results")
    else:
        try:
            body, rows = dune.results(f"{BASE_URL}/query/{query_id}/results")
        except DuneError as e:
            if len(e.args) > 1 and e.args[1] == 404:
                raise DuneError(f"{e.args[0]} Dune keeps no current result for query {query_id} (it may never "
                                "have run, its SQL may have changed since, or the result has expired). Choose "
                                "'Execute and retrieve latest results' to run it.")
            raise
except DuneError as e:
    omniscope_api.abort(e.args[0])

metadata = (body.get("result") or {}).get("metadata") or {}
results = rows_frame(rows, metadata)
omniscope_api.write_output_records(execution_frame(body, len(results)), output_number=0)
omniscope_api.write_output_records(results, output_number=1)
partial = " (partial result: Dune stopped the query early)" if body.get("state") == PARTIAL else ""
omniscope_api.close(f"Query {query_id}: {len(results)} rows, {len(results.columns)} columns{partial}.")
