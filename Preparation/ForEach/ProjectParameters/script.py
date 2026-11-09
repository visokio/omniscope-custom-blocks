"""Project Parameters Batch Setting.

For each input record, sets project parameters of the Omniscope project whose address is in the record. A field
named like a parameter sets that parameter. Uses each project's Workflow REST API: POST <project>/w/updateparams.
The input records are passed through to the output unchanged.
"""
import json
import re
from urllib.parse import quote

import pandas as pd
import urllib3

from omniscope.api import OmniscopeApi

api = OmniscopeApi()

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
        return None
    return quote(found.group(1), safe=":/%@!$&'()*+,;=-._~") + "/"


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

    def set_parameters(self, names, values, what):
        updates = [{"name": n, "value": v} for n, v in zip(names, values)]
        status, data = self.call("POST", "w/updateparams", {"updates": updates})
        if status != 200 or data.get("status") != "SUCCESS":
            api.abort(self.failure(what, status, data, PARAMS_PERMISSION))


# ---------------------------------------------------------------- options
url_field = api.get_option("Iox_File_Url")
param_names = list(api.get_option("Parameters") or [])

records = api.read_input_records(input_number=0)
if records is None:
    api.abort("Connect the records: one per project to update, with the project's address and one field per "
              "parameter.")
if not url_field:
    api.abort("Choose the field holding the project addresses.")
if not param_names:
    api.abort("Choose the parameter fields: each field's name must be the name of a parameter in the projects.")
missing = [n for n in [url_field] + param_names if n not in records.columns]
if missing:
    api.abort("Not in the input: " + ", ".join(missing))
param_names = [n for n in param_names if n != url_field]
if not param_names:
    api.abort("The parameter fields must be other than the project address field.")

username, password = api.get_option("username"), api.get_option("password")

# ---------------------------------------------------------------- check every address before changing anything
addresses = []
for number, text in enumerate(records[url_field].astype(object).tolist(), start=1):
    base = project_url(text if isinstance(text, str) else "")
    if base is None:
        api.abort(f"Record {number}: the project address must end in .iox, for example "
                  f"http://127.0.0.1:24679/Folder/Project.iox/ (got {text!r}).")
    addresses.append(base)

# ---------------------------------------------------------------- one update per record
projects = {}
rows = record_values(records, param_names)
for number, (base, values) in enumerate(zip(addresses, rows), start=1):
    project = projects.setdefault(base, Project(base, username, password))
    send_update(f"Record {number} of {len(rows)}: {base} ({describe(param_names, values)})")
    project.set_parameters(param_names, values, f"Record {number}: setting parameters of {base}")

api.write_output(records, "output")
api.close(f"Set {len(param_names)} parameter(s) in {len(rows)} record(s), {len(projects)} project(s)."
          if rows else "No records in the input: nothing was set.")
