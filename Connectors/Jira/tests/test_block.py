"""Tests for the Jira block against canned Jira responses (tests/canned/, written by tests/make_canned.py).
No test calls Jira: requests.Session.request is replaced by a fake that answers from the canned files."""

import json
import os
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
AUTH = {"jiraInstance": "example", "username": "analyst@example.com", "apiKey": "secret-token"}


def canned(name):
    with open(os.path.join(CANNED, name), encoding="utf-8") as fh:
        return json.load(fh)


def response(status, body):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body).encode("utf-8")
    r.headers["Content-Type"] = "application/json"
    r.url = "https://example.atlassian.net/"
    return r


class FakeJira:
    """Answers like Jira Cloud from canned pages, and records every request."""

    def __init__(self, issue_pages=None, status=200):
        self.calls = []
        self.issue_pages = (
            issue_pages if issue_pages is not None else [canned("issues-page-1.json"), canned("issues-page-2.json")]
        )
        self.status = status

    def __call__(self, session, method, url, params=None, **kw):
        self.calls.append({"method": method, "url": url, "params": dict(params or {}), "auth": session.auth})
        if self.status != 200:
            return response(self.status, {"errorMessages": ["Client must be authenticated to access this resource."]})
        if url.endswith("/rest/api/2/project/search"):
            return response(200, canned("projects.json"))
        if url.endswith("/rest/api/2/project"):  # the older, unpaged list (still served)
            return response(200, canned("projects.json")["values"])
        if url.endswith("/rest/api/2/search") or "/rest/api/2/search?" in url:
            # Jira Cloud has removed the old search endpoint: it answers 410 Gone
            return response(
                410,
                {
                    "errorMessages": [
                        "The requested API has been removed. Please migrate to the /rest/api/3/search/jql API."
                    ]
                },
            )
        if url.endswith("/rest/api/2/search/jql"):
            page = 1 if params.get("nextPageToken") == "page-2-token" else 0
            return response(200, self.issue_pages[page])
        return response(404, {"errorMessages": [f"no canned answer for {url}"]})

    def issue_calls(self):
        return [c for c in self.calls if c["url"].endswith("/search/jql")]


def install(monkeypatch, fake):
    """Route every requests call to the fake (a plain function, so it binds like the method it replaces)."""
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def jira(monkeypatch):
    return install(monkeypatch, FakeJira())


def test_projects_and_issues_of_a_project(jira):
    res = run_block(HERE, None, {**AUTH, "projectID": "SHOP"}).raise_for_error()
    projects, issues = res.output(0), res.output(1)
    assert projects["Project key"].tolist() == ["SHOP", "APP", "OPS"]
    assert projects["Category"].tolist()[0] == "Customer facing" and pd.isna(projects["Category"][1])
    assert projects["Team-managed"].tolist() == [False, True, False]
    # both pages are read
    assert len(issues) == 42 and issues["Key"].is_unique
    assert issues.columns[:6].tolist() == ["Key", "Issue ID", "Project key", "Issue type", "Summary", "Status"]
    first = issues.iloc[0]
    assert first["Key"] == "SHOP-2" and first["Summary"] == "Basket total ignores voucher after page refresh"
    assert first["Assignee"] == "Priya Natarajan" and first["Components"] == "Checkout"
    assert first["Fix versions"] == "2025.11"
    assert issues.loc[issues["Key"] == "SHOP-3", "Labels"].item() == "customer-reported"
    # dates are dates, in UTC
    assert str(issues["Created"].dt.tz) == "UTC"
    assert issues["Created"].iloc[0] == pd.Timestamp("2025-09-01T08:15:00Z")
    assert issues["Status category"].value_counts()["Done"] == 14
    # no list or dict values reach Omniscope
    for c in issues.columns:
        assert not issues[c].map(lambda v: isinstance(v, (list, dict))).any(), c
    assert res.final_message == "Loaded 42 issues."


def test_requests_use_the_current_search_endpoint_and_pages(jira):
    run_block(HERE, None, {**AUTH, "projectID": "SHOP"}).raise_for_error()
    calls = jira.issue_calls()
    assert len(calls) == 2
    assert calls[0]["url"] == "https://example.atlassian.net/rest/api/2/search/jql"
    assert calls[0]["params"]["jql"] == 'project = "SHOP" ORDER BY key ASC'
    assert "summary" in calls[0]["params"]["fields"] and "nextPageToken" not in calls[0]["params"]
    assert calls[1]["params"]["nextPageToken"] == "page-2-token"
    assert calls[0]["auth"].username == "analyst@example.com" and calls[0]["auth"].password == "secret-token"


def test_site_can_be_given_as_a_url(jira):
    run_block(HERE, None, {**AUTH, "jiraInstance": " https://example.atlassian.net/jira/your-work "}).raise_for_error()
    assert jira.calls[0]["url"] == "https://example.atlassian.net/rest/api/2/project/search"


def test_jql_filter_with_and_without_a_project(jira):
    run_block(HERE, None, {**AUTH, "projectID": "SHOP", "jql": "status != Done ORDER BY created DESC"})
    run_block(HERE, None, {**AUTH, "jql": "assignee = currentUser()"})
    first, second = jira.issue_calls()[0], jira.issue_calls()[2]
    assert first["params"]["jql"] == 'project = "SHOP" AND (status != Done) ORDER BY created DESC'
    assert second["params"]["jql"] == "assignee = currentUser()"


def test_extra_fields_are_added_as_text_or_numbers(jira):
    issues = (
        run_block(HERE, None, {**AUTH, "projectID": "SHOP", "extraFields": "customfield_10016, reporter"})
        .raise_for_error()
        .output(1)
    )
    assert "customfield_10016" in issues.columns and "reporter" in issues.columns
    assert "customfield_10016" in jira.issue_calls()[0]["params"]["fields"]
    assert issues["customfield_10016"].iloc[1] == 2 and pd.isna(issues["customfield_10016"].iloc[0])
    assert issues["reporter"].iloc[0] == "Elena Rossi"


def test_only_projects_when_no_project_or_jql(jira):
    res = run_block(HERE, None, AUTH).raise_for_error()
    assert len(res.output(0)) == 3 and res.output(1) is None
    assert jira.issue_calls() == []
    assert "Enter a project key" in res.final_message


def test_blank_project_is_treated_as_unset(jira):
    # The original block searched for "project=" (an error) when the option was cleared to empty text
    res = run_block(HERE, None, {**AUTH, "projectID": "  "}).raise_for_error()
    assert jira.issue_calls() == [] and res.output(1) is None


def test_project_with_no_issues_gives_empty_output_with_fields(monkeypatch):
    fake = FakeJira(issue_pages=[{"issues": [], "isLast": True}])
    install(monkeypatch, fake)
    issues = run_block(HERE, None, {**AUTH, "projectID": "APP"}).raise_for_error().output(1)
    assert len(issues) == 0 and "Summary" in issues.columns and "Created" in issues.columns


def test_bad_credentials_abort_with_a_message(monkeypatch):
    install(monkeypatch, FakeJira(status=401))
    res = run_block(HERE, None, {**AUTH, "projectID": "SHOP"})
    assert res.status == "aborted" and "API token" in res.final_message
    res = run_block(HERE, None, {**AUTH, "apiKey": None})
    assert res.status == "aborted" and "API token" in res.final_message


def test_many_issues(monkeypatch):
    base = canned("issues-page-1.json")["issues"][0]
    big = [dict(base, key=f"SHOP-{i}", id=str(i)) for i in range(20_000)]
    pages = {}

    def fake(session, method, url, params=None, **kw):
        if url.endswith("/project/search"):
            return response(200, canned("projects.json"))
        start = int(params.get("nextPageToken") or 0)
        nxt = start + 100
        pages[start] = True
        return response(200, {"issues": big[start:nxt], "isLast": nxt >= len(big), "nextPageToken": str(nxt)})

    install(monkeypatch, fake)
    t0 = time.time()
    issues = run_block(HERE, None, {**AUTH, "projectID": "SHOP"}).raise_for_error().output(1)
    assert len(issues) == 20_000 and len(pages) == 200
    assert time.time() - t0 < 60


def test_placeholder_matches_the_canned_output(jira):
    issues = run_block(HERE, None, {**AUTH, "projectID": "SHOP"}).raise_for_error().output(1)
    placeholder = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"), dtype=str, keep_default_na=False)
    assert placeholder.columns.tolist() == issues.columns.tolist()
    assert placeholder["Key"].tolist() == issues["Key"].tolist()
