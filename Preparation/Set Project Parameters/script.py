"""Set Project Parameters.

Sets parameters of one Omniscope project (often the project this block is in) from records holding a parameter
name and a value. All values are sent in one request to the project's Workflow REST API
(POST <project>/w/updateparams), so either all of them are set or none is.
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
        # waitForIdle false: don't wait for the project to be idle (it may be the project running this block).
        status, data = self.call("POST", "w/updateparams", {"updates": updates, "waitForIdle": False})
        if status != 200 or data.get("status") != "SUCCESS":
            api.abort(self.failure(what, status, data, PARAMS_PERMISSION))


def project_address(text):
    base = project_url(text)
    if base is None:
        api.abort("Project address: give the address of an Omniscope project ending in .iox, for example "
                  "http://127.0.0.1:24679/Folder/Project.iox/ (got " + (repr(text) if text else "nothing") + ").")
    return base


# ---------------------------------------------------------------- options
base = project_address(api.get_option("Iox_File_Url"))
name_field = api.get_option("Params_Name")
value_field = api.get_option("Params_Value")

records = api.read_input_records(input_number=0)
if records is None:
    api.abort("Connect the records: one per parameter, with the parameter's name and its new value.")
if not name_field or not value_field:
    api.abort("Choose the field holding the parameter names and the field holding the values.")
missing = [n for n in (name_field, value_field) if n not in records.columns]
if missing:
    api.abort("Not in the input: " + ", ".join(missing))

names = [json_value(v) for v in records[name_field].astype(object).tolist()]
for number, name in enumerate(names, start=1):
    if name is None or str(name).strip() == "":
        api.abort(f"Record {number} has no parameter name.")
names = [str(n).strip() for n in names]
values = [row[0] for row in record_values(records, [value_field])]

# A name given twice: the later record wins (only one value can be set).
last = {name: i for i, name in enumerate(names)}
keep = sorted(last.values())
names = [names[i] for i in keep]
values = [values[i] for i in keep]

if names:
    send_update(f"Setting {len(names)} parameter(s) of {base}...")
    Project(base, api.get_option("username"), api.get_option("password")).set_parameters(
        names, values, f"Setting parameters ({describe(names, values)})")

api.write_output(records.iloc[keep].reset_index(drop=True), "set")
api.close(f"Set {len(names)} parameter(s): {describe(names, values)}." if names
          else "No records in the input: nothing was set.")
