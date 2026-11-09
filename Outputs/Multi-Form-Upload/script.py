"""Multipart Form Upload: posts files to an HTTP endpoint as multipart/form-data, one request per file, and records
each answer: the files listed in a field of the input records, or a single chosen file when no input is connected."""
import mimetypes
import os

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

MAX_RESPONSE_LENGTH = 8000
REQUEST_TIMEOUT_SECONDS = 30

# Headers added to every request, in addition to the Headers and Authorization options,
# for example {"ApiKey": "abc123"}. The options take precedence over these.
CUSTOM_HEADERS: dict = {}

api = OmniscopeApi()


def truncate_text(text):
    if text is None:
        return ""
    return text if len(text) <= MAX_RESPONSE_LENGTH else text[:MAX_RESPONSE_LENGTH] + "... [truncated]"


def parse_lines(text, separator, what):
    """'Name: value' (headers) or 'name=value' (form fields), one per line; blank lines are skipped."""
    pairs = []
    for number, line in enumerate(str(text or "").splitlines(), start=1):
        if not line.strip():
            continue
        if separator not in line:
            api.abort(f"{what}, line {number}: expected name{separator}value, got: {line.strip()}")
        name, value = line.split(separator, 1)
        if not name.strip():
            api.abort(f"{what}, line {number}: the name is empty.")
        pairs.append((name.strip(), value.strip()))
    return pairs


def upload_file(url, path, field_name, headers, form_fields):
    mime_type, _ = mimetypes.guess_type(path)
    with open(path, "rb") as handle:
        files = {field_name: (os.path.basename(path), handle, mime_type or "application/octet-stream")}
        return requests.post(url, headers=headers, data=form_fields, files=files, timeout=REQUEST_TIMEOUT_SECONDS)


def is_missing(value):
    return value is None or (not isinstance(value, str) and pd.isna(value)) or str(value).strip() == ""


upload_url = api.get_option("upload_url")
single_file = api.get_option("file_path_column")
path_field = api.get_option("file_path_field")
form_field_name = (api.get_option("form_field_name") or "").strip() or "file"
header_text = api.get_option("headers")
authorization = api.get_option("authorization")
extra_text = api.get_option("extra_fields")

if not upload_url or not str(upload_url).strip():
    api.abort("Enter the upload URL.")
upload_url = str(upload_url).strip()
if not upload_url.lower().startswith(("http://", "https://")):
    api.abort(f"The upload URL must start with http:// or https://, got: {upload_url}")

headers = dict(CUSTOM_HEADERS)
headers.update(parse_lines(header_text, ":", "Headers"))
if authorization:
    headers["Authorization"] = authorization
form_fields = parse_lines(extra_text, "=", "Extra form fields")

input_data = api.read_input_records(input_number=0)
if input_data is not None:
    if not path_field:
        api.abort("An input is connected: choose the field that holds the file paths.")
    output = input_data.copy()
    paths = [None if is_missing(v) else str(v).strip() for v in input_data[path_field].tolist()]
else:
    if not single_file:
        api.abort("Choose the file to upload, or connect records with a field of file paths.")
    output = pd.DataFrame({"File path": [single_file]})
    paths = [single_file]

statuses, bodies, errors = [], [], []
for number, path in enumerate(paths, start=1):
    status, body, error = None, "", ""
    if path is None:
        error = "No file path"
    elif not os.path.isfile(path):
        error = f"File not found: {path}"
    else:
        api.update_message(f"Uploading {number} of {len(paths)}: {os.path.basename(path)}")
        try:
            response = upload_file(upload_url, path, form_field_name, headers, form_fields)
            status = response.status_code
            body = truncate_text(response.text)
            if not response.ok:
                error = f"HTTP {status} {response.reason or ''}".strip()
        except requests.RequestException as exc:
            error = f"{type(exc).__name__}: {exc}"
    statuses.append(status)
    bodies.append(body)
    errors.append(error)

output["HTTP status"] = pd.array(statuses, dtype="Int64")
output["Response"] = bodies
output["Error"] = errors
api.write_output_records(output, output_number=0)
failed = sum(1 for e in errors if e)
api.commit(f"Uploaded {len(paths) - failed} of {len(paths)} file(s)" + (f"; {failed} failed (see Error)." if failed else "."))
