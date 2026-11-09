"""Conditional Execution.

When its yes/no option is on (usually linked to a project parameter), starts a separate execution of the listed
blocks of an Omniscope project, through the project's Workflow REST API (POST <project>/w/execute). It does not
wait for that execution to finish. When the option is off it does nothing.
"""
import json
import re
from urllib.parse import quote

import urllib3

from omniscope.api import OmniscopeApi

api = OmniscopeApi()

EXECUTE_PERMISSION = "Workflow Execution via APIs"


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

    def start(self, blocks, refresh):
        # cancelExisting true: a run of the project already in progress is cancelled so that this one starts;
        # waitForIdle false: the request returns at once, without waiting for that project to be idle.
        payload = {"blocks": blocks, "refreshFromSource": refresh, "cancelExisting": True, "waitForIdle": False}
        status, data = self.call("POST", "w/execute", payload)
        if status != 200 or not data.get("jobId"):
            api.abort(self.failure("Starting the blocks", status, data, EXECUTE_PERMISSION))
        return str(data["jobId"])


def project_address(text):
    base = project_url(text)
    if base is None:
        api.abort("Project address: give the address of an Omniscope project ending in .iox, for example "
                  "http://127.0.0.1:24679/Folder/Project.iox/ (got " + (repr(text) if text else "nothing") + ").")
    return base


def block_list(text):
    """Comma-separated block names; blank entries (a trailing comma, an emptied option) are dropped."""
    return [name.strip() for name in (text or "").split(",") if name.strip()]


def is_on(value):
    """The yes/no option, also when linked to a parameter that holds the text "true"."""
    return value is True or str(value).strip().lower() == "true"


if not is_on(api.get_option("execute")):
    api.close("Run the blocks is off: nothing was started.")
else:
    base = project_address(api.get_option("Iox_File_Url"))
    blocks = block_list(api.get_option("Block_Names"))
    if not blocks:
        api.abort("List the blocks to run, separated by commas. (An empty list would run the whole workflow, "
                  "including this block if the address is this project.)")
    refresh = bool(api.get_option("Refresh_From_Source"))
    send_update("Starting " + ", ".join(blocks) + "...")
    job_id = Project(base, api.get_option("username"), api.get_option("password")).start(blocks, refresh)
    api.close(f"Started {', '.join(blocks)} (job {job_id}). This block does not wait for them to finish.")
