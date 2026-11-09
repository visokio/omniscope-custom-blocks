"""Tests for the Slack Web API block against canned Slack answers (tests/canned/, written by tests/make_canned.py).
No test calls Slack: requests.Session.request is replaced by a fake that answers from the canned files and records
the request that would have been sent."""

import json
import os
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
TOKEN = {"authToken": "xoxb-test-token"}


def canned(name):
    with open(os.path.join(CANNED, name), encoding="utf-8") as fh:
        return json.load(fh)


def response(status, body, headers=None):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body).encode("utf-8")
    r.headers.update(headers or {})
    r.url = "https://slack.com/api/"
    return r


class FakeSlack:
    def __init__(self, answers=None):
        self.calls = []
        self.answers = answers or {}

    def __call__(self, session, method, url, params=None, json=None, headers=None, **kw):
        name = url.rsplit("/", 1)[-1]
        self.calls.append(
            {
                "verb": method,
                "url": url,
                "method": name,
                "params": dict(params or {}),
                "json": json,
                "headers": dict(session.headers, **(headers or {})),
            }
        )
        if name in self.answers:
            answer = self.answers[name]
            return answer(self) if callable(answer) else response(200, answer)
        args = params if method == "GET" else json
        if name == "conversations.list":
            page = 2 if (args or {}).get("cursor") == "dGVhbTpDMDE1" else 1
            return response(200, canned(f"conversations-list-{page}.json"))
        if name == "users.profile.get":
            return response(200, canned("users-profile-get.json"))
        if name == "chat.postMessage":
            return response(200, canned("chat-postMessage.json"))
        return response(404, {})


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def slack(monkeypatch):
    return install(monkeypatch, FakeSlack())


def test_channels_become_records_across_pages(slack):
    res = run_block(HERE, None, {**TOKEN, "methodName": "conversations.list"}).raise_for_error()
    channels = res.output(0)
    assert len(channels) == 24 and channels["name"].iloc[0] == "general" and channels["id"].is_unique
    assert {"topic.value", "purpose.value", "num_members", "is_private"} <= set(channels.columns)
    assert channels.loc[channels["name"] == "sales-uk", "previous_names"].item() == '["sales"]'
    assert channels["num_members"].sum() == 1430
    for c in channels.columns:
        assert not channels[c].map(lambda v: isinstance(v, (list, dict))).any(), c
    raw = res.output(1)
    assert raw.columns.tolist() == ["Text Response"] and len(raw) == 2
    assert json.loads(raw["Text Response"][0])["channels"][0]["name"] == "general"
    assert res.final_message == "24 records from 'channels', 2 pages."


def test_requests_sent_for_a_get(slack):
    run_block(HERE, None, {**TOKEN, "methodName": "conversations.list", "params": '{"limit": 15}'}).raise_for_error()
    first, second = slack.calls
    assert first["verb"] == "GET" and first["url"] == "https://slack.com/api/conversations.list"
    assert first["params"] == {"limit": 15} and second["params"] == {"limit": 15, "cursor": "dGVhbTpDMDE1"}
    assert first["headers"]["Authorization"] == "Bearer xoxb-test-token"


def test_post_message_request_and_one_record(slack):
    payload = {"channel": "C01000EXAMPLE", "text": "Weekly sales report is ready"}
    res = run_block(
        HERE,
        None,
        {**TOKEN, "methodName": "chat.postMessage", "methodType": "POST", "jsonPayload": json.dumps(payload)},
    ).raise_for_error()
    assert len(slack.calls) == 1
    call = slack.calls[0]
    assert call["verb"] == "POST" and call["json"] == payload and call["params"] == {}
    record = res.output(0)
    assert len(record) == 1 and record["message.text"].item() == "Weekly sales report is ready"
    assert record["ts"].item() == "1735732800.000100" and "ok" not in record.columns
    assert record["message.blocks"].item() == '[{"type": "rich_text"}]'


def test_answer_without_a_list_is_one_record(slack):
    # users.profile.get answers with one object; the original gave one record with a dict in it
    record = run_block(HERE, None, {**TOKEN, "methodName": "users.profile.get"}).raise_for_error().output(0)
    assert len(record) == 1 and record["profile.real_name"].item() == "Ada Example"


def test_records_from_a_chosen_key_and_first_page_only(slack):
    res = run_block(
        HERE, None, {**TOKEN, "methodName": "conversations.list", "recordsFrom": "channels", "followPages": False}
    ).raise_for_error()
    assert len(res.output(0)) == 15 and len(slack.calls) == 1
    res = run_block(HERE, None, {**TOKEN, "methodName": "conversations.list", "recordsFrom": "members"})
    assert res.status == "aborted" and "has no 'members'" in res.final_message


def test_list_of_ids_and_an_empty_list(monkeypatch):
    install(
        monkeypatch,
        FakeSlack(
            {
                "conversations.members": {
                    "ok": True,
                    "members": ["U01", "U02", "U03"],
                    "response_metadata": {"next_cursor": ""},
                },
                "conversations.history": {"ok": True, "messages": [], "has_more": False},
            }
        ),
    )
    out = run_block(HERE, None, {**TOKEN, "methodName": "conversations.members", "params": '{"channel": "C1"}'})
    assert out.raise_for_error().output(0)["value"].tolist() == ["U01", "U02", "U03"]
    out = run_block(HERE, None, {**TOKEN, "methodName": "conversations.history"}).raise_for_error().output(0)
    assert len(out) == 0 and out.columns.tolist() == ["messages"]


def test_slack_errors_stop_the_block_with_its_message(monkeypatch):
    # The original wrote Slack's error answer ({"ok": false, ...}) as if it were data, or raised a traceback
    install(monkeypatch, FakeSlack({"conversations.list": canned("error-missing-scope.json")}))
    res = run_block(HERE, None, {**TOKEN, "methodName": "conversations.list"})
    assert res.status == "aborted"
    assert (
        res.final_message == "Slack refused conversations.list: missing_scope (the token needs the channels:read scope)"
    )


def test_bad_options(slack):
    res = run_block(HERE, None, {**TOKEN, "params": "{'user': 'U1'}"})
    assert res.status == "aborted" and "not valid JSON" in res.final_message
    res = run_block(HERE, None, {**TOKEN, "params": "[1, 2]"})
    assert res.status == "aborted" and "JSON object" in res.final_message
    res = run_block(HERE, None, {"methodName": "conversations.list"})
    assert res.status == "aborted" and "token" in res.final_message
    res = run_block(HERE, None, {**TOKEN, "methodName": "no.such.method"})
    assert res.status == "aborted" and "no method called" in res.final_message
    assert run_block(HERE, None, {**TOKEN, "params": ""}).raise_for_error()  # empty means no arguments


def test_default_options_need_no_user_id(slack):
    # The original's default arguments named one particular user id
    run_block(HERE, None, TOKEN).raise_for_error()
    assert slack.calls[0]["method"] == "conversations.list" and slack.calls[0]["params"] == {}


def test_rate_limit_is_waited_out(monkeypatch):
    state = {"n": 0}

    def limited(fake):
        state["n"] += 1
        if state["n"] == 1:
            return response(429, {"ok": False, "error": "ratelimited"}, {"Retry-After": "0"})
        return response(200, canned("users-profile-get.json"))

    install(monkeypatch, FakeSlack({"users.profile.get": limited}))
    out = run_block(HERE, None, {**TOKEN, "methodName": "users.profile.get"}).raise_for_error().output(0)
    assert state["n"] == 2 and len(out) == 1


def test_many_pages(monkeypatch):
    template = canned("conversations-list-1.json")["channels"][0]

    def paged(fake):
        n = len(fake.calls)
        chans = [dict(template, id=f"C{n}-{i}", name=f"c{n}-{i}") for i in range(200)]
        return response(
            200, {"ok": True, "channels": chans, "response_metadata": {"next_cursor": "" if n == 100 else f"cur{n}"}}
        )

    install(monkeypatch, FakeSlack({"conversations.list": paged}))
    t0 = time.time()
    res = run_block(HERE, None, {**TOKEN, "methodName": "conversations.list"}).raise_for_error()
    assert len(res.output(0)) == 20_000 and len(res.output(1)) == 100
    assert time.time() - t0 < 60


def test_placeholder_matches_the_canned_output(slack):
    channels = run_block(HERE, None, {**TOKEN, "methodName": "conversations.list"}).raise_for_error().output(0)
    placeholder = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"), dtype=str, keep_default_na=False)
    assert placeholder.columns.tolist() == channels.columns.tolist()
    assert placeholder["id"].tolist() == channels["id"].tolist()
