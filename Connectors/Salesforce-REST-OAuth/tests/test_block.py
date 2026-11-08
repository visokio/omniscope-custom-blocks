"""Tests for the Salesforce REST OAuth block against canned Salesforce responses (tests/canned/, written by
tests/make_canned.py). No test calls Salesforce: requests.Session.request is replaced by a fake that answers from the
canned files and records each request."""

import json
import os
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
INSTANCE = "https://acme-dev.my.salesforce.com"
AUTH = {"authBaseUrl": "https://acme-dev.my.salesforce.com/", "clientId": "3MVG9-test-key", "clientSecret": "s3cret"}


def canned(name):
    with open(os.path.join(CANNED, name), encoding="utf-8") as fh:
        return json.load(fh)


def response(status, body, headers=None):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body).encode("utf-8")
    r.headers.update(headers or {})
    r.url = INSTANCE
    return r


class FakeSalesforce:
    def __init__(self, answers=None):
        self.calls = []
        self.answers = answers or {}

    def __call__(self, session, method, url, headers=None, params=None, data=None, timeout=None, **kw):
        path = url[len(INSTANCE) :]
        self.calls.append(
            {
                "method": method,
                "path": path,
                "params": dict(params or {}),
                "data": data,
                "headers": dict(headers or {}),
                "timeout": timeout,
            }
        )
        if path in self.answers:
            answer = self.answers[path]
            return answer(self) if callable(answer) else response(200, answer)
        if path == "/services/oauth2/token" and method == "POST":
            if data.get("client_secret") != "s3cret":
                return response(400, {"error": "invalid_client", "error_description": "invalid client credentials"})
            return response(200, canned("token.json"))
        if path == "/services/data/":
            return response(200, canned("versions.json"))
        if path == "/services/data/v62.0/sobjects":
            return response(200, canned("sobjects.json"))
        if path == "/services/data/v62.0/sobjects/Account/describe":
            return response(200, canned("describe-account.json"))
        if path in ("/services/data/v62.0/query", "/services/data/v62.0/queryAll"):
            if "FROM Contact" in params["q"]:
                return response(200, canned("query-contacts-owner.json"))
            return response(200, canned("query-accounts-1.json"))
        if path == "/services/data/v62.0/query/01gA0000000Example-2000":
            return response(200, canned("query-accounts-2.json"))
        return response(404, [{"errorCode": "NOT_FOUND", "message": "The requested resource does not exist"}])

    def queries(self):
        return [c for c in self.calls if c["path"].endswith(("/query", "/queryAll"))]


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def salesforce(monkeypatch):
    return install(monkeypatch, FakeSalesforce())


def test_simple_mode_loads_accounts_with_dates_as_dates(salesforce):
    res = run_block(HERE, None, AUTH).raise_for_error()  # Load data, Simple, Accounts are the defaults
    out = res.output(0)
    assert len(out) == 12 and out["Id"].is_unique
    assert out.columns.tolist() == [
        "Id",
        "IsDeleted",
        "Name",
        "Type",
        "Industry",
        "BillingStreet",
        "BillingCity",
        "BillingPostalCode",
        "BillingCountry",
        "AnnualRevenue",
        "NumberOfEmployees",
        "OwnerId",
        "CreatedDate",
        "LastActivityDate",
    ]
    # date-time and date fields, typed from Describe
    assert str(out["CreatedDate"].dt.tz) == "UTC" and out["CreatedDate"].iloc[0] == pd.Timestamp("2024-01-01T09:30Z")
    assert out["LastActivityDate"].iloc[0] == pd.Timestamp("2025-01-10", tz="UTC") and pd.isna(
        out["LastActivityDate"][3]
    )
    assert out["AnnualRevenue"].iloc[0] == 2400000 and pd.isna(out["AnnualRevenue"].iloc[2])
    assert res.final_message == "Loaded 12 Salesforce records using REST API v62.0."


def test_simple_mode_requests(salesforce):
    run_block(HERE, None, AUTH).raise_for_error()
    token = salesforce.calls[0]
    assert token["path"] == "/services/oauth2/token" and token["method"] == "POST"
    assert token["data"] == {
        "grant_type": "client_credentials",
        "client_id": "3MVG9-test-key",
        "client_secret": "s3cret",
    }
    assert [c["path"] for c in salesforce.calls[1:]] == [
        "/services/data/",
        "/services/data/v62.0/sobjects/Account/describe",
        "/services/data/v62.0/query",
        "/services/data/v62.0/query/01gA0000000Example-2000",
    ]
    soql = salesforce.queries()[0]["params"]["q"]
    # compound BillingAddress (its parts are loaded) and the deprecated field are left out
    assert soql.startswith("SELECT Id, IsDeleted, Name,") and soql.endswith(" FROM Account")
    assert "BillingAddress" not in soql and "Jigsaw" not in soql and "BillingCity" in soql
    assert all(c["headers"].get("Authorization") == "Bearer 00Dxx0000000001!AQ0AQtest" for c in salesforce.calls[1:])


def test_query_builder_and_include_deleted(salesforce):
    out = run_block(
        HERE,
        None,
        {
            **AUTH,
            "queryMode": "builder",
            "objectName": "Account",
            "fields": "Id, Name, CreatedDate",
            "whereClause": "Industry = 'Retail'",
            "orderBy": "Name",
            "includeDeleted": "true",
        },
    )
    out.raise_for_error()
    q = salesforce.queries()[0]
    assert q["path"].endswith("/queryAll")
    assert q["params"]["q"] == "SELECT Id, Name, CreatedDate FROM Account WHERE Industry = 'Retail' ORDER BY Name"
    # without Describe, text in Salesforce's date-time format is still read as a date
    assert str(out.output(0)["CreatedDate"].dt.tz) == "UTC"


def test_custom_soql_relationships_without_empty_placeholders(salesforce):
    # The original gave a field "Owner" (all empty) beside "Owner.Name" when one owner was null
    out = run_block(
        HERE, None, {**AUTH, "queryMode": "soql", "soql": "SELECT Id, LastName, Owner.Name, Account.Name FROM Contact"}
    )
    out = out.raise_for_error().output(0)
    assert out.columns.tolist() == ["Id", "LastName", "Owner.Name", "Account.Name"]
    assert out["Owner.Name"].tolist()[0] == "Ada Example" and pd.isna(out["Owner.Name"][1])
    assert out["Account.Name"].tolist()[1] == "Marsh Lane Hardware"


def test_no_records_keeps_the_fields(monkeypatch):
    # The original wrote no output at all, so downstream blocks lost their fields
    empty = {"totalSize": 0, "done": True, "records": []}
    install(monkeypatch, FakeSalesforce({"/services/data/v62.0/query": empty}))
    res = run_block(HERE, None, AUTH).raise_for_error()
    assert len(res.output(0)) == 0 and "CreatedDate" in res.output(0).columns
    res = run_block(HERE, None, {**AUTH, "queryMode": "builder", "fields": "Id, Name, Owner.Name"}).raise_for_error()
    assert res.output(0).columns.tolist() == ["Id", "Name", "Owner.Name"]
    res = run_block(HERE, None, {**AUTH, "queryMode": "soql", "soql": "SELECT Id FROM Account"}).raise_for_error()
    assert res.output(0) is None and "0 records" in res.final_message


def test_maximum_records_is_reported(salesforce):
    res = run_block(HERE, None, {**AUTH, "maxRecords": "5"}).raise_for_error()
    assert len(res.output(0)) == 5 and len(salesforce.queries()) == 1
    assert "Stopped at Maximum records (5)" in res.final_message


def test_schema_actions(salesforce):
    objects = (
        run_block(HERE, None, {**AUTH, "operation": "list_objects", "apiVersion": "62"}).raise_for_error().output(0)
    )
    assert objects["name"].tolist() == ["Account", "Contact", "Opportunity", "Delivery_Route__c"]
    assert not any(c["path"] == "/services/data/" for c in salesforce.calls)  # a given version is not looked up
    fields = run_block(HERE, None, {**AUTH, "operation": "describe_fields"}).raise_for_error().output(0)
    assert len(fields) == 16 and fields.loc[fields["name"] == "OwnerId", "referenceTo"].item() == "User"


def test_errors_stop_with_salesforce_message(monkeypatch, salesforce):
    res = run_block(HERE, None, {**AUTH, "clientSecret": "wrong"})
    assert res.status == "aborted" and "invalid_client: invalid client credentials" in res.final_message
    assert "wrong" not in res.final_message
    res = run_block(HERE, None, {**AUTH, "authBaseUrl": "http://acme.my.salesforce.com"})
    assert res.status == "aborted" and "HTTPS" in res.final_message
    res = run_block(HERE, None, {**AUTH, "queryMode": "builder", "fields": "Id, COUNT(Id)"})
    assert res.status == "aborted" and "Invalid field API name" in res.final_message
    res = run_block(HERE, None, {**AUTH, "maxRecords": "lots"})
    assert res.status == "aborted" and "must be an integer" in res.final_message


def test_transient_errors_are_retried(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    state = {"n": 0}

    def flaky(fake):
        state["n"] += 1
        if state["n"] == 1:
            return response(503, [{"errorCode": "SERVER_UNAVAILABLE", "message": "try again"}], {"Retry-After": "0"})
        return response(200, canned("versions.json"))

    install(monkeypatch, FakeSalesforce({"/services/data/": flaky}))
    run_block(HERE, None, {**AUTH, "operation": "list_objects"}).raise_for_error()
    assert state["n"] == 2


def test_many_records(monkeypatch):
    template = canned("query-accounts-1.json")["records"][0]

    def page(n):
        def answer(fake):
            rows = [dict(template, Id=f"001{n:04d}{i:05d}") for i in range(2000)]
            body = {"totalSize": 40_000, "done": n == 19, "records": rows}
            if n < 19:
                body["nextRecordsUrl"] = f"/services/data/v62.0/query/loc-{n + 1}"
            return response(200, body)

        return answer

    answers = {"/services/data/v62.0/query": page(0)}
    answers.update({f"/services/data/v62.0/query/loc-{n}": page(n) for n in range(1, 20)})
    install(monkeypatch, FakeSalesforce(answers))
    t0 = time.time()
    out = run_block(HERE, None, {**AUTH, "maxRecords": "0"}).raise_for_error().output(0)
    assert len(out) == 40_000 and out["Id"].is_unique
    assert time.time() - t0 < 60


def test_placeholder_matches_the_canned_output(salesforce):
    out = run_block(HERE, None, AUTH).raise_for_error().output(0)
    placeholder = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"), dtype=str, keep_default_na=False)
    assert placeholder.columns.tolist() == out.columns.tolist()
    assert placeholder["Id"].tolist() == out["Id"].tolist()
