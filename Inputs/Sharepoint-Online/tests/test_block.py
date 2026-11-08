"""Tests for the SharePoint Online Downloader block against canned Microsoft Graph responses (tests/canned/, written
by tests/make_canned.py). No test calls Microsoft: requests.Session.request is replaced by a fake that answers from the
canned files and records every request."""
import base64
import json
import os
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
GRAPH = "https://graph.microsoft.com/v1.0"
DRIVE = "b!Docs0000000000000000000000000000000000000000000000000001"
FOLDER = "https://contoso.sharepoint.com/sites/Finance/Shared%20Documents/Reports"
FILE = "https://contoso.sharepoint.com/sites/Finance/Shared Documents/Reports/budget-2025.csv"
AUTH = {"tenantId": "contoso.onmicrosoft.com", "clientId": "11111111-2222-3333-4444-555555555555",
        "clientSecret": "invented-secret"}


def canned(name):
    with open(os.path.join(CANNED, name), encoding="utf-8") as fh:
        return json.load(fh)


def response(status, body=None, content=None):
    r = requests.Response()
    r.status_code = status
    r._content = content if content is not None else json.dumps(body).encode()
    r._content_consumed = True
    r.headers["Content-Type"] = "application/octet-stream" if content is not None else "application/json"
    return r


class FakeGraph:
    def __init__(self, token_status=200, drive_status=200, children_pages=None):
        self.calls = []
        self.token_status, self.drive_status = token_status, drive_status
        self.children_pages = children_pages

    def __call__(self, session, method, url, data=None, **kw):
        self.calls.append({"method": method, "url": url, "data": data,
                           "auth": session.headers.get("Authorization")})
        if url.startswith("https://login.microsoftonline.com/"):
            return response(self.token_status, canned("token.json" if self.token_status == 200 else "token-error.json"))
        if url == f"{GRAPH}/sites/contoso.sharepoint.com:/sites/Finance":
            return response(self.drive_status, canned("site.json" if self.drive_status == 200 else "forbidden.json"))
        if url.endswith("/drives") and "/sites/" in url:
            return response(200, canned("drives.json"))
        if url == f"{GRAPH}/drives/{DRIVE}/root:/Reports/budget-2025.csv":
            return response(200, canned("item-file.json"))
        if url == f"{GRAPH}/drives/{DRIVE}/root:/Reports":
            return response(200, canned("item-folder.json"))
        if url.startswith(f"{GRAPH}/shares/u!"):
            return response(200, canned("item-file.json"))
        if "/children" in url:
            if self.children_pages is not None:
                page = int(url.rsplit("page", 1)[1]) if "skiptoken=page" in url else 0
                return response(200, self.children_pages[page])
            return response(200, canned("children-page-2.json" if "skiptoken=page2" in url else "children-page-1.json"))
        if url.endswith("/content"):
            item_id = url.split("/items/")[1].split("/")[0]
            names = {"01FILEBUDGET000000000000000000001": "budget-2025.csv",
                     "01FILEHEADCOUNT00000000000000002": "headcount.csv", "01FILESUPPLIERS00000000000000003": "suppliers.csv"}
            if item_id in names:
                with open(os.path.join(CANNED, "files", names[item_id]), "rb") as fh:
                    return response(200, content=fh.read())
            return response(200, content=b"x")
        return response(404, canned("not-found.json"))


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def graph(monkeypatch):
    return install(monkeypatch, FakeGraph())


def run(tmp_path, url, **options):
    return run_block(HERE, None, {**AUTH, "fileUrl": url, "localFolder": str(tmp_path / "downloads"), **options})


def test_one_file(graph, tmp_path):
    res = run(tmp_path, FILE).raise_for_error()
    out = res.output(0)
    assert out["File name"].tolist() == ["budget-2025.csv"]
    assert out["File path"].tolist() == [str(tmp_path / "downloads" / "budget-2025.csv")]
    assert (tmp_path / "downloads" / "budget-2025.csv").read_text().startswith("Cost centre,Month,Budget")
    assert out["Size (bytes)"].tolist() == [os.path.getsize(os.path.join(CANNED, "files", "budget-2025.csv"))]
    assert out["Modified"].iloc[0] == pd.Timestamp("2025-03-10 08:12:45")
    token = graph.calls[0]
    assert token["url"] == "https://login.microsoftonline.com/contoso.onmicrosoft.com/oauth2/v2.0/token"
    assert token["data"]["grant_type"] == "client_credentials"
    assert token["data"]["scope"] == "https://graph.microsoft.com/.default"
    assert all(c["auth"] == "Bearer " + canned("token.json")["access_token"] for c in graph.calls[1:])


def test_every_file_of_a_folder_over_two_pages(graph, tmp_path):
    out = run(tmp_path, FOLDER).raise_for_error().output(0)
    # sorted by name; the Archive sub-folder is skipped
    assert out["File name"].tolist() == ["budget-2025.csv", "headcount.csv", "suppliers.csv"]
    assert (tmp_path / "downloads" / "headcount.csv").read_text().startswith("Department,Headcount")
    assert len([c for c in graph.calls if "/children" in c["url"]]) == 2


def test_urls_copied_from_the_browser(graph, tmp_path):
    url = ("https://contoso.sharepoint.com/:x:/r/sites/Finance/Shared%20Documents/Reports/budget-2025.csv"
           "?d=w0c1e2d3&csf=1&web=1")
    assert run(tmp_path, url).raise_for_error().output(0)["File name"].tolist() == ["budget-2025.csv"]
    share = "https://contoso.sharepoint.com/:x:/s/Finance/EaBcDeFgHiJkLmNoPq?e=AbC123"
    run(tmp_path, share).raise_for_error()
    token = "u!" + base64.urlsafe_b64encode(share.encode()).decode().rstrip("=")
    assert any(c["url"] == f"{GRAPH}/shares/{token}/driveItem" for c in graph.calls)


def test_sign_in_failure_gives_microsofts_reason(monkeypatch, tmp_path):
    install(monkeypatch, FakeGraph(token_status=401))
    res = run(tmp_path, FILE)
    assert res.status == "aborted" and "AADSTS7000215: Invalid client secret" in res.final_message
    assert "Trace ID" not in res.final_message


def test_missing_permission_and_unknown_items(monkeypatch, tmp_path):
    install(monkeypatch, FakeGraph(drive_status=403))
    res = run(tmp_path, FILE)
    assert res.status == "aborted" and "Sites.Read.All" in res.final_message
    install(monkeypatch, FakeGraph())
    res = run(tmp_path, FILE.replace("budget-2025", "budget-2030"))
    assert res.status == "aborted" and "404" in res.final_message and "could not be found" in res.final_message
    res = run(tmp_path, "https://contoso.sharepoint.com/sites/Finance/SitePages/Home.aspx")
    assert res.status == "aborted" and "Documents, Board papers" in res.final_message


def test_option_checks(graph, tmp_path):
    assert "Client secret" in run(tmp_path, FILE, clientSecret=None).final_message
    assert "File or folder URL" in run(tmp_path, " ").final_message
    res = run(tmp_path, "contoso.sharepoint.com/sites/Finance/x.csv")
    assert res.status == "aborted" and "https://" in res.final_message
    assert graph.calls == []


def test_empty_folder(monkeypatch, tmp_path):
    install(monkeypatch, FakeGraph(children_pages=[{"value": []}]))
    out = run(tmp_path, FOLDER).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["File path", "File name", "Size (bytes)", "Modified", "SharePoint URL"]


def test_large_folder(monkeypatch, tmp_path):
    pages = []
    for p in range(10):
        values = [{"id": f"ID{p}-{k}", "name": f"part-{p:02d}-{k:03d}.csv", "size": 1,
                   "lastModifiedDateTime": "2025-03-01T00:00:00Z", "file": {},
                   "parentReference": {"driveId": DRIVE}} for k in range(200)]
        body = {"value": values}
        if p < 9:
            body["@odata.nextLink"] = f"{GRAPH}/drives/{DRIVE}/items/F/children?$skiptoken=page{p + 1}"
        pages.append(body)
    install(monkeypatch, FakeGraph(children_pages=pages))
    t0 = time.time()
    out = run(tmp_path, FOLDER).raise_for_error().output(0)
    assert time.time() - t0 < 60 and len(out) == 2000
