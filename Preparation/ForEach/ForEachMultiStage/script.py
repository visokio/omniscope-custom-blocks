"""For Each Multi Stage.

Runs another Omniscope project once per input record, in up to three stages per record (each stage a separate
workflow execution of its own list of blocks, started when the previous one has finished), with an optional
stage run once before the loop. Before each record's stages it sets the project's parameters from the record's
fields. It uses the project's Workflow REST API: POST <project>/w/updateparams, POST <project>/w/execute and
GET <project>/w/job/<id>/state.
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
before = (block_list(api.get_option("Block_Names_Before")), bool(api.get_option("Refresh_From_Source_Before")))
stages = [
    (block_list(api.get_option("Block_Names")), bool(api.get_option("Refresh_From_Source"))),
    (block_list(api.get_option("Block_Names2")), bool(api.get_option("Refresh_From_Source2"))),
    (block_list(api.get_option("Block_Names3")), bool(api.get_option("Refresh_From_Source3"))),
]
# Stage 1 always runs (no blocks listed: the whole workflow); stages 2 and 3 only when they list blocks.
stages = [stages[0]] + [s for s in stages[1:] if s[0]]
ignore_errors = bool(api.get_option("ignore_errors"))
busy_minutes = api.get_option("busy_wait_minutes")
busy_minutes = 10 if busy_minutes is None else max(0, busy_minutes)

records = api.read_input_records(input_number=0)
if records is None:
    api.abort("Connect the records to loop over: one record per pass, one field per project parameter.")
if not param_names:
    api.abort("Choose the parameter fields: each field's name must be the name of a parameter in the project.")
missing = [n for n in param_names if n not in records.columns]
if missing:
    api.abort("Not in the input: " + ", ".join(missing))

project = Project(base, api.get_option("username"), api.get_option("password"))


def run_stage(label, blocks, refresh):
    """Start one execution and wait for it; returns (state, job id)."""
    send_update(label + ("" if not blocks else ": " + ", ".join(blocks)) + "...")
    job_id = project.start(blocks, refresh, busy_minutes)
    return project.wait(job_id, busy_minutes), job_id


# ---------------------------------------------------------------- before the loop
if before[0]:
    state, job_id = run_stage("Before the loop", *before)
    if state != "COMPLETED":
        api.abort(f"The stage before the loop ended {state} (job {job_id}). Open the project to see why.")

# ---------------------------------------------------------------- loop
runs = records[param_names].copy().reset_index(drop=True)
results, failed_stage, job_ids = [], [], []
rows = record_values(records, param_names)
for number, values in enumerate(rows, start=1):
    project.set_parameters(param_names, values)
    result, at_stage, ids = "COMPLETED", None, []
    for stage_number, (blocks, refresh) in enumerate(stages, start=1):
        state, job_id = run_stage(f"Pass {number} of {len(rows)} ({describe(param_names, values)}), "
                                  f"stage {stage_number}", blocks, refresh)
        ids.append(job_id)
        if state != "COMPLETED":
            result, at_stage = state, stage_number
            break
    results.append(result)
    failed_stage.append(at_stage)
    job_ids.append(", ".join(ids))
    if result != "COMPLETED" and not ignore_errors:
        api.abort(f"Pass {number} ({describe(param_names, values)}) ended {result} at stage {at_stage}. Open the "
                  "project to see why, or tick 'Carry on after a failed pass'.")

taken = set(runs.columns)
runs.insert(0, unique_name("Pass", taken), pd.Series(range(1, len(runs) + 1), dtype="int64"))
taken = set(runs.columns)
runs[unique_name("Result", taken)] = pd.Series(results, dtype=object)
taken = set(runs.columns)
runs[unique_name("Failed at stage", taken)] = pd.Series(failed_stage, dtype="Int64")
taken = set(runs.columns)
runs[unique_name("Job IDs", taken)] = pd.Series(job_ids, dtype=object)
api.write_output(runs, "passes")

failed = sum(1 for r in results if r != "COMPLETED")
if not rows:
    api.close("No records in the input: nothing was run" + (" after the stage before the loop." if before[0] else "."))
else:
    api.close(f"{len(rows)} passes, {len(rows) - failed} completed" + (f", {failed} failed" if failed else "") + ".")
