"""Tests for the Multipart Form Upload block. No request leaves the machine: requests.Session.send is replaced by a
fake endpoint that records each prepared request (so the tests can check the multipart body and headers) and answers
with the canned responses in tests/canned/."""
import os
import re
import shutil
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
FILES = os.path.join(HERE, "sample-data", "files")
LIST = os.path.join(HERE, "sample-data", "upload-list.csv")
CANNED = os.path.join(HERE, "tests", "canned")
URL = "https://uploads.example.com/api/files"


def canned(name):
    with open(os.path.join(CANNED, name), encoding="utf-8") as fh:
        return fh.read()


class FakeEndpoint:
    def __init__(self, reject=(), fail=()):
        self.requests = []
        self.reject, self.fail = reject, fail

    def __call__(self, session, request, **kwargs):
        self.requests.append(request)
        body = request.body or b""
        if any(name.encode() in body for name in self.fail):
            raise requests.ConnectionError("Connection reset by peer")
        r = requests.Response()
        r.request, r.url = request, request.url
        r.headers["Content-Type"] = "application/json"
        if any(name.encode() in body for name in self.reject):
            r.status_code, r.reason, r._content = 415, "Unsupported Media Type", canned("rejected-415.json").encode()
        else:
            # the canned answer names the file it received, with an id per upload
            name = re.search(rb'filename="([^"]+)"', body).group(1).decode()
            text = canned("accepted.json").replace("FILENAME", name).replace("ID", f"{len(self.requests):04d}")
            r.status_code, r.reason, r._content = 201, "Created", text.encode()
        return r


@pytest.fixture
def endpoint(monkeypatch):
    fake = FakeEndpoint()
    monkeypatch.setattr(requests.Session, "send", lambda session, request, **kw: fake(session, request, **kw))
    return fake


@pytest.fixture
def files(tmp_path):
    target = tmp_path / "files"
    shutil.copytree(FILES, target)
    return target


def upload_list(files):
    df = pd.read_csv(LIST)
    df["File path"] = [str(files / name) for name in df["File name"]]
    return df


def test_one_request_per_record_with_results(endpoint, files):
    res = run_block(HERE, upload_list(files), {"upload_url": URL, "file_path_field": "File path"}).raise_for_error()
    out = res.output(0)
    assert len(endpoint.requests) == 4  # INV-1005 is listed but has no file
    assert out["HTTP status"].tolist()[:4] == [201] * 4 and pd.isna(out["HTTP status"].iloc[4])
    assert out["Error"].tolist() == ["", "", "", "", f"File not found: {files / 'INV-1005.csv'}"]
    assert out["Response"].tolist()[:2] == ['{"status": "received", "file": "INV-1001.csv", "id": "upl-0001"}',
                                            '{"status": "received", "file": "INV-1002.csv", "id": "upl-0002"}']
    assert list(out.columns) == ["Invoice", "File name", "File path", "HTTP status", "Response", "Error"]
    assert res.final_message == "Uploaded 4 of 5 file(s); 1 failed (see Error)."


def test_the_request_is_multipart_with_the_file(endpoint, files):
    run_block(HERE, upload_list(files).iloc[:1], {"upload_url": URL, "file_path_field": "File path",
                                                   "form_field_name": "document"}).raise_for_error()
    req = endpoint.requests[0]
    assert req.method == "POST" and req.url == URL
    assert req.headers["Content-Type"].startswith("multipart/form-data; boundary=")
    body = req.body.decode()
    assert 'Content-Disposition: form-data; name="document"; filename="INV-1001.csv"' in body
    assert "Content-Type: text/csv" in body
    assert "INV-1001,Fernhill Garden Centre,2025-03-03,420.00,84.00,504.00" in body


def test_headers_authorization_and_extra_fields(endpoint, files):
    # The original block could only send headers written into the script, and had no extra form fields
    options = {"upload_url": URL, "file_path_field": "File path", "headers": "X-Api-Key: abc123\n\nX-Source: omniscope",
               "authorization": "Bearer t0ken", "extra_fields": "folder=invoices/2025\nnotify = yes"}
    run_block(HERE, upload_list(files).iloc[:1], options).raise_for_error()
    req = endpoint.requests[0]
    assert req.headers["X-Api-Key"] == "abc123" and req.headers["X-Source"] == "omniscope"
    assert req.headers["Authorization"] == "Bearer t0ken"
    body = req.body.decode()
    assert 'name="folder"\r\n\r\ninvoices/2025\r\n' in body and 'name="notify"\r\n\r\nyes\r\n' in body


def test_badly_written_headers_abort(endpoint, files):
    res = run_block(HERE, upload_list(files), {"upload_url": URL, "file_path_field": "File path",
                                              "headers": "X-Api-Key abc123"})
    assert res.status == "aborted" and "Headers, line 1" in res.final_message and not endpoint.requests


def test_single_file_when_nothing_is_connected(endpoint, files):
    # The original block's only mode; the output fields are now named like the rest of the block
    res = run_block(HERE, None, {"upload_url": URL, "file_path_column": str(files / "INV-1002.csv")}).raise_for_error()
    out = res.output(0)
    assert out["File path"].tolist() == [str(files / "INV-1002.csv")] and out["HTTP status"].tolist() == [201]
    assert b'filename="INV-1002.csv"' in endpoint.requests[0].body


def test_rejections_and_connection_failures_are_recorded(monkeypatch, files):
    fake = FakeEndpoint(reject=("INV-1002",), fail=("INV-1003",))
    monkeypatch.setattr(requests.Session, "send", lambda session, request, **kw: fake(session, request, **kw))
    out = run_block(HERE, upload_list(files).iloc[:4], {"upload_url": URL, "file_path_field": "File path"})
    out = out.raise_for_error().output(0)
    assert out["HTTP status"].tolist()[:2] == [201, 415] and pd.isna(out["HTTP status"].iloc[2])
    assert out["Error"].iloc[1] == "HTTP 415 Unsupported Media Type"
    assert "Only CSV and PDF" in out["Response"].iloc[1]
    assert out["Error"].iloc[2].startswith("ConnectionError")
    assert out["Error"].iloc[3] == ""


def test_long_responses_are_truncated(monkeypatch, files):
    def send(session, request, **kw):
        r = requests.Response()
        r.status_code, r._content, r.request = 200, b"x" * 20000, request
        return r
    monkeypatch.setattr(requests.Session, "send", send)
    out = run_block(HERE, None, {"upload_url": URL, "file_path_column": str(files / "INV-1001.csv")})
    body = out.raise_for_error().output(0)["Response"].iloc[0]
    assert body.endswith("... [truncated]") and len(body) == 8000 + len("... [truncated]")


def test_option_checks(endpoint, files):
    # The original raised ValueError (a Python error, not a message) for a missing URL
    assert "Enter the upload URL" in run_block(HERE, None, {"upload_url": None}).final_message
    res = run_block(HERE, None, {"upload_url": "uploads.example.com/api", "file_path_column": str(files / "INV-1001.csv")})
    assert res.status == "aborted" and "http://" in res.final_message
    res = run_block(HERE, upload_list(files), {"upload_url": URL})
    assert res.status == "aborted" and "choose the field" in res.final_message
    assert run_block(HERE, None, {"upload_url": URL}).status == "aborted"
    assert not endpoint.requests


def test_empty_input_and_missing_paths(endpoint, files):
    empty = pd.DataFrame({"File path": pd.Series([], dtype=object)})
    out = run_block(HERE, empty, {"upload_url": URL, "file_path_field": "File path"}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["File path", "HTTP status", "Response", "Error"]
    df = pd.DataFrame({"File path": [None, str(files / "INV-1001.csv")]})
    out = run_block(HERE, df, {"upload_url": URL, "file_path_field": "File path"}).raise_for_error().output(0)
    assert out["Error"].tolist() == ["No file path", ""] and len(endpoint.requests) == 1


def test_many_files(endpoint, tmp_path):
    for k in range(2000):
        (tmp_path / f"f{k}.txt").write_text(f"row {k}\n")
    df = pd.DataFrame({"Path": [str(tmp_path / f"f{k}.txt") for k in range(2000)]})
    t0 = time.time()
    out = run_block(HERE, df, {"upload_url": URL, "file_path_field": "Path"}).raise_for_error().output(0)
    assert time.time() - t0 < 60
    assert (out["HTTP status"] == 201).all() and len(endpoint.requests) == 2000
