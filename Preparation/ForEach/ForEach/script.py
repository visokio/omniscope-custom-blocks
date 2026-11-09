"""For Each (Separate Workflows).

Runs another Omniscope project once per input record. Before each run it sets the project's parameters from the
record's fields, then starts the workflow and waits for it to finish. It uses the project's Workflow REST API:
POST <project>/w/updateparams, POST <project>/w/execute and GET <project>/w/job/<id>/state.
"""
import json
import re
import time
from urllib.parse import quote

import pandas as pd
import urllib3

from omniscope.api import OmniscopeApi

api = OmniscopeApi()

STILL_RUNNING = {"QUEUED", "RUNNING", "BLOCKED"}
EXECUTE_PERMISSION = "Workflow Execution via APIs"
PARAMS_PERMISSION = "Project parameters access via APIs"


def send_update(text):
    try:
        api.update_message(text)
    except Exception:  # older servers have no update_message
        pass


def project_url(text):
    """The project's base address, ending in '.iox/'. A pasted report or workflow address is cut back to it."""
    text = (text or "").strip()
    found = re.match(r"(?i)^(https?://[^?#]*?\.iox)(?=[/?#]|$)", text)
    if not found:
        api.abort("Project address: give the address of an Omniscope project ending in .iox, for example "
                  "http://127.0.0.1:24679/Folder/Project.iox/ (got " + (repr(text) if text else "nothing") + ").")
    return quote(found.group(1), safe=":/%@!$&'()*+,;=-._~") + "/"


def block_list(text):
    """Comma-separated block names; blank entries (a trailing comma, an emptied option) are dropped."""
    return [name.strip() for name in (text or "").split(",") if name.strip()]


def json_value(value):
    """A record's value as JSON: missing -> null, dates -> ISO 8601 text, numpy scalars -> Python numbers."""
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):  # numpy scalar
        value = value.item()
        if isinstance(value, float) and value != value:
            return None
    return value


def record_values(frame, fields):
    """One list of JSON-ready values per record, keeping integers as integers."""
    columns = [[json_value(v) for v in frame[f].astype(object).tolist()] for f in fields]
    return [list(values) for values in zip(*columns)] if columns else []


def describe(names, values):
    return ", ".join(f"{n} = {v}" for n, v in zip(names, values))


class Project:
    def __init__(self, base, username, password):
        self.base = base
        self.http = urllib3.PoolManager()
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if username:
            self.headers.update(urllib3.make_headers(basic_auth=f"{username}:{password or ''}"))

    def call(self, method, path, payload=None):
        body = None if payload is None else json.dumps(payload, allow_nan=False)
        try:
            response = self.http.request(method, self.base + path, headers=self.headers, body=body,
                                         timeout=urllib3.Timeout(connect=10, read=120))
        except urllib3.exceptions.HTTPError as exc:
            api.abort(f"Could not reach {self.base}: {exc}")
        try:
            data = json.loads(response.data.decode("utf-8")) if response.data else {}
        except (ValueError, UnicodeDecodeError):
            data = {}
        return response.status, data if isinstance(data, dict) else {}

    def failure(self, what, status, data, permission):
        detail = data.get("errorMessage") or data.get("errorType") or ""
        text = f"{what} failed (HTTP {status}" + (f": {detail}" if detail else "") + ")."
        if status in (401, 403):
            text += (f" The server refused the request: the user needs the '{permission}' permission, or give a "
                     "username and password.")
        elif status == 404 and not data.get("errorType"):
            text += f" Is there a project at {self.base}?"
        return text

    def set_parameters(self, names, values):
        updates = [{"name": n, "value": v} for n, v in zip(names, values)]
        status, data = self.call("POST", "w/updateparams", {"updates": updates})
        if status != 200 or data.get("status") != "SUCCESS":
            api.abort(self.failure(f"Setting parameters ({describe(names, values)})", status, data,
                                   PARAMS_PERMISSION))

    def start(self, blocks, refresh, busy_minutes):
        payload = {"blocks": blocks, "refreshFromSource": refresh, "cancelExisting": False}
        give_up = None
        while True:
            status, data = self.call("POST", "w/execute", payload)
            if status == 200 and data.get("jobId"):
                return str(data["jobId"])
            if data.get("errorType") == "WORKFLOW_ALREADY_RUNNING" or status == 409:
                if give_up is None:
                    give_up = time.monotonic() + 60 * busy_minutes
                    send_update("The project is already running; waiting for it to finish...")
                if time.monotonic() >= give_up:
                    api.abort(f"The project at {self.base} was still busy after {busy_minutes:g} minutes, so the "
                              "run could not start. (A project cannot run itself: the address must be another "
                              "project.)")
                time.sleep(2)
                continue
            api.abort(self.failure("Starting the workflow", status, data, EXECUTE_PERMISSION))

    def wait(self, job_id, busy_minutes):
        polls, queued_since = 0, None
        while True:
            time.sleep(1 if polls < 30 else 5)
            polls += 1
            status, data = self.call("GET", "w/job/" + quote(job_id, safe="") + "/state")
            if status != 200 or not data.get("jobState"):
                api.abort(self.failure(f"Checking run {job_id}", status, data, EXECUTE_PERMISSION))
            state = data["jobState"]
            if state not in STILL_RUNNING:
                return state
            if state != "QUEUED":
                queued_since = None
                continue
            queued_since = queued_since or time.monotonic()
            if time.monotonic() - queued_since >= 60 * busy_minutes:
                api.abort(f"Run {job_id} was still queued after {busy_minutes:g} minutes. This block's own "
                          "workflow is running too, so the server must allow at least 2 workflow jobs at once "
                          "(Admin app > Advanced > Concurrent Workflow Jobs).")


def unique_name(name, taken):
    while name in taken:
        name = name + " (For Each)"
    return name


# ---------------------------------------------------------------- options
base = project_url(api.get_option("Iox_File_Url"))
param_names = list(api.get_option("Parameters") or [])
block_names = block_list(api.get_option("Block_Names"))
refresh = bool(api.get_option("Refresh_From_Source"))
ignore_errors = bool(api.get_option("ignore_errors"))
busy_minutes = api.get_option("busy_wait_minutes")
busy_minutes = 10 if busy_minutes is None else max(0, busy_minutes)

records = api.read_input_records(input_number=0)
if records is None:
    api.abort("Connect the records to loop over: one record per run, one field per project parameter.")
if not param_names:
    api.abort("Choose the parameter fields: each field's name must be the name of a parameter in the project.")
missing = [n for n in param_names if n not in records.columns]
if missing:
    api.abort("Not in the input: " + ", ".join(missing))

project = Project(base, api.get_option("username"), api.get_option("password"))

# ---------------------------------------------------------------- runs
runs = records[param_names].copy().reset_index(drop=True)
results, job_ids = [], []
rows = record_values(records, param_names)
for number, values in enumerate(rows, start=1):
    project.set_parameters(param_names, values)
    send_update(f"Run {number} of {len(rows)}: {describe(param_names, values)}")
    job_id = project.start(block_names, refresh, busy_minutes)
    state = project.wait(job_id, busy_minutes)
    results.append(state)
    job_ids.append(job_id)
    if state != "COMPLETED" and not ignore_errors:
        api.abort(f"Run {number} ({describe(param_names, values)}) ended {state}. Open the project to see why, or "
                  "tick 'Carry on after a failed run'.")

taken = set(runs.columns)
runs.insert(0, unique_name("Run", taken), pd.Series(range(1, len(runs) + 1), dtype="int64"))
taken = set(runs.columns)
runs[unique_name("Result", taken)] = pd.Series(results, dtype=object)
taken = set(runs.columns)
runs[unique_name("Job ID", taken)] = pd.Series(job_ids, dtype=object)
api.write_output(runs, "runs")

failed = sum(1 for r in results if r != "COMPLETED")
if not rows:
    api.close("No records in the input: nothing was run.")
else:
    api.close(f"{len(rows)} runs, {len(rows) - failed} completed" + (f", {failed} failed" if failed else "") + ".")
