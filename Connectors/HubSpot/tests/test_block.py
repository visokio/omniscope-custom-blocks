"""Tests for the HubSpot block against canned HubSpot responses (tests/canned/, written by tests/make_canned.py).
No test calls HubSpot: requests.Session.request is replaced by a fake that answers from the canned files."""

import json
import os
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
TOKEN = {"key": "pat-eu1-test"}
API = "https://api.hubapi.com"


def canned(name):
    with open(os.path.join(CANNED, name), encoding="utf-8") as fh:
        return json.load(fh)


def response(status, body, headers=None):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body).encode("utf-8")
    r.headers.update(headers or {})
    r.url = API
    return r


class FakeHubSpot:
    def __init__(self, answers=None):
        self.calls = []
        self.answers = answers or {}

    def __call__(self, session, method, url, params=None, json=None, headers=None, **kw):
        path = url[len(API) :]
        self.calls.append(
            {"method": method, "path": path, "params": dict(params or {}), "json": json, "headers": headers or {}}
        )
        if path in self.answers:
            answer = self.answers[path]
            return answer(self) if callable(answer) else response(200, answer)
        if path == "/crm/v3/objects/companies":
            return response(
                200,
                canned("companies-page-2.json" if (params or {}).get("after") == "9009" else "companies-page-1.json"),
            )
        if path == "/crm/v3/objects/contacts":
            return response(200, canned("contacts.json"))
        if path == "/crm/v3/objects/contacts/search":
            return response(200, canned("search-contacts.json"))
        if path == "/crm/v3/associations/contacts/companies/batch/read":
            return response(200, canned("associations.json"))
        if path == "/crm/v3/lists/search":
            return response(200, canned("lists.json"))
        if path == "/forms/v2/forms":
            return response(200, canned("forms.json"))
        if path.startswith("/form-integrations/v1/submissions/forms/"):
            return response(200, canned("form-submissions.json"))
        return response(404, {"status": "error", "message": f"Unable to infer object type from: {path}"})


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def hubspot(monkeypatch):
    return install(monkeypatch, FakeHubSpot())


def no_nested_values(df):
    for c in df.columns:
        assert not df[c].map(lambda v: isinstance(v, (list, dict))).any(), c


def test_companies_across_pages(hubspot):
    res = run_block(HERE, None, TOKEN).raise_for_error()  # Companies is the default action
    out = res.output(0)
    assert len(out) == 12 and out["id"].is_unique
    assert out["properties.name"].iloc[0] == "Fernhill Garden Centre"
    assert [c["params"].get("after") for c in hubspot.calls] == [None, "9009"]
    assert hubspot.calls[0]["headers"]["Authorization"] == "Bearer pat-eu1-test"
    # HubSpot's timestamps become dates; property values stay as HubSpot sends them
    assert str(out["createdAt"].dt.tz) == "UTC" and str(out["properties.createdate"].dt.tz) == "UTC"
    assert out["createdAt"].iloc[0] == pd.Timestamp("2024-01-03T09:10:00Z")
    assert out["properties.hs_object_id"].iloc[0] == "9001"
    assert res.final_message == "Loaded 12 records."


def test_properties_option_is_sent(hubspot):
    run_block(HERE, None, {**TOKEN, "properties": "name, domain ,industry"}).raise_for_error()
    assert hubspot.calls[0]["params"]["properties"] == "name,domain,industry"
    run_block(HERE, None, {**TOKEN, "object": "list_contacts"}).raise_for_error()
    assert hubspot.calls[-1]["params"]["properties"] == "email,firstname,lastname,lifecyclestage"


def test_search_contacts_and_companies(hubspot):
    out = (
        run_block(HERE, None, {**TOKEN, "object": "search_contact", "params": "brookside"}).raise_for_error().output(0)
    )
    assert out["properties.lastname"].tolist() == ["Rossi"]
    assert hubspot.calls[0]["json"]["query"] == "brookside"
    res = run_block(HERE, None, {**TOKEN, "object": "search_company", "params": "garden", "properties": "name,city"})
    assert hubspot.calls[-1]["path"] == "/crm/v3/objects/companies/search"
    assert hubspot.calls[-1]["json"]["properties"] == ["name", "city"]
    res = run_block(HERE, None, {**TOKEN, "object": "search_contact"})
    assert res.status == "aborted" and "text to search" in res.final_message


def test_associations_with_capitalised_object_names(hubspot):
    # The original sent "Contacts"/"Companies" (its own defaults) as typed; HubSpot's object types are lower case
    out = (
        run_block(
            HERE,
            None,
            {**TOKEN, "object": "batch_associations", "from_object_type": "Contacts", "to_object_type": "Companies"},
        )
        .raise_for_error()
        .output(0)
    )
    paths = [c["path"] for c in hubspot.calls]
    assert paths == ["/crm/v3/objects/contacts", "/crm/v3/associations/contacts/companies/batch/read"]
    assert hubspot.calls[1]["json"] == {"inputs": [{"id": str(i)} for i in range(501, 507)]}
    assert out.columns.tolist() == ["contacts_id", "companies_id", "association_type"]
    assert out.values.tolist() == [
        ["501", "9001", "contact_to_company"],
        ["503", "9003", "contact_to_company"],
        ["503", "9008", "contact_to_company"],
    ]


def test_associations_for_given_ids(hubspot):
    run_block(HERE, None, {**TOKEN, "object": "batch_associations", "object_ids": "501, 503,"}).raise_for_error()
    assert [c["path"] for c in hubspot.calls] == ["/crm/v3/associations/contacts/companies/batch/read"]
    assert hubspot.calls[0]["json"] == {"inputs": [{"id": "501"}, {"id": "503"}]}


def test_lists_and_forms_have_no_nested_values(hubspot):
    # The original wrote lists and objects (filterBranch, formFieldGroups) into fields as Python text
    lists = run_block(HERE, None, {**TOKEN, "object": "list_lists"}).raise_for_error().output(0)
    assert lists["name"].tolist() == ["Spring newsletter", "Trade customers"]
    no_nested_values(lists)
    forms = run_block(HERE, None, {**TOKEN, "object": "list_forms"}).raise_for_error().output(0)
    no_nested_values(forms)
    assert json.loads(forms["formFieldGroups"].item()) == [{"fields": [{"name": "email"}]}]


def test_form_submissions(hubspot):
    out = (
        run_block(
            HERE, None, {**TOKEN, "object": "list_form_submissions", "params": "3f1c0f9e-0000-4000-8000-000000000001"}
        )
        .raise_for_error()
        .output(0)
    )
    assert out["email"].tolist() == ["ben@example.com", "chloe@example.com"]
    assert out["firstname"].tolist()[0] == "Ben" and pd.isna(out["firstname"].tolist()[1])
    res = run_block(HERE, None, {**TOKEN, "object": "list_form_submissions"})
    assert res.status == "aborted" and "form's ID" in res.final_message


def test_no_records(monkeypatch):
    install(monkeypatch, FakeHubSpot({"/crm/v3/objects/deals": {"results": []}}))
    res = run_block(HERE, None, {**TOKEN, "object": "list_deals"}).raise_for_error()
    assert res.output(0) is None and res.final_message == "HubSpot returned no records."


def test_errors_stop_the_block_with_a_message(monkeypatch):
    # The original raised requests' HTTPError, a traceback without HubSpot's explanation
    install(monkeypatch, FakeHubSpot({"/crm/v3/objects/companies": lambda f: response(401, {"message": "expired"})}))
    res = run_block(HERE, None, TOKEN)
    assert res.status == "aborted" and "access token" in res.final_message
    install(
        monkeypatch,
        FakeHubSpot(
            {
                "/crm/v3/objects/leads": lambda f: response(
                    403, {"message": "This app hasn't been granted all required scopes to make this call."}
                )
            }
        ),
    )
    res = run_block(HERE, None, {**TOKEN, "object": "list_leads"})
    assert res.status == "aborted" and "required scopes" in res.final_message
    res = run_block(HERE, None, {"object": "list_leads"})
    assert res.status == "aborted" and "access token" in res.final_message
    res = run_block(HERE, None, {**TOKEN, "object": "batch_associations", "from_object_type": "contacts; drop"})
    assert res.status == "aborted" and "not a HubSpot object type" in res.final_message


def test_rate_limit_is_waited_out(monkeypatch):
    state = {"n": 0}

    def limited(fake):
        state["n"] += 1
        if state["n"] == 1:
            return response(429, {"message": "You have reached your secondly limit."}, {"Retry-After": "0"})
        return response(200, canned("contacts.json"))

    install(monkeypatch, FakeHubSpot({"/crm/v3/objects/contacts": limited}))
    out = run_block(HERE, None, {**TOKEN, "object": "list_contacts"}).raise_for_error().output(0)
    assert state["n"] == 2 and len(out) == 6


def test_many_pages(monkeypatch):
    template = canned("companies-page-1.json")["results"][0]

    def paged(fake):
        start = int(fake.calls[-1]["params"].get("after") or 0)
        rows = [dict(template, id=str(start + i)) for i in range(100)]
        body = {"results": rows}
        if start + 100 < 20_000:
            body["paging"] = {"next": {"after": str(start + 100)}}
        return response(200, body)

    install(monkeypatch, FakeHubSpot({"/crm/v3/objects/companies": paged}))
    t0 = time.time()
    out = run_block(HERE, None, TOKEN).raise_for_error().output(0)
    assert len(out) == 20_000 and out["id"].is_unique
    assert time.time() - t0 < 60


def test_placeholder_matches_the_canned_output(hubspot):
    out = run_block(HERE, None, TOKEN).raise_for_error().output(0)
    placeholder = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"), dtype=str, keep_default_na=False)
    assert placeholder.columns.tolist() == out.columns.tolist()
    assert placeholder["id"].tolist() == out["id"].tolist()
