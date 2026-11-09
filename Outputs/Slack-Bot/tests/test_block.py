"""Tests for Slack Bot. Nothing is sent to Slack: requests.post is replaced by a stand-in that records each request
and answers with the canned Slack responses in tests/canned/, so the tests check every request the block would
send."""
import json
import os
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "stock-alerts.csv")
CANNED = os.path.join(HERE, "tests", "canned")
TOKEN = "xoxb-test-token"
SETTINGS = {"authToken": TOKEN, "channelID": "C0123ABCD", "message": "Message"}


def canned(name):
    with open(os.path.join(CANNED, name + ".json"), encoding="utf-8") as fh:
        return fh.read().encode("utf-8")


def response(status, body):
    r = requests.Response()
    r.status_code = status
    r._content = body
    return r


class FakeSlack:
    def __init__(self, fail=None, fail_after=0):
        self.calls = []
        self.fail, self.fail_after = fail, fail_after

    def __call__(self, url, data=None, headers=None, files=None, timeout=None, **kw):
        if hasattr(data, "read"):
            data = data.read()
        self.calls.append({"url": url, "data": data, "headers": headers or {}, "files": files, "timeout": timeout})
        method = url.rsplit("/", 1)[-1]
        if url.startswith("https://files.slack.com/upload/"):
            return response(200, b"OK - " + str(len(data)).encode())
        if self.fail and len(self.calls) > self.fail_after:
            if self.fail == "http":
                return response(500, b"<html>Server error</html>")
            if self.fail == "network":
                raise requests.ConnectionError("Failed to establish a new connection")
            return response(200, canned("error." + self.fail))
        return response(200, canned(method))

    def posts(self):
        return [json.loads(c["data"]) for c in self.calls if c["url"].endswith("chat.postMessage")]


@pytest.fixture
def slack(monkeypatch):
    fake = FakeSlack()
    monkeypatch.setattr(requests, "post", fake)
    return fake


def test_sample_posts_one_message_per_record(slack):
    res = run_block(HERE, SAMPLE, SETTINGS).raise_for_error()
    posts = slack.posts()
    assert len(posts) == 5 and all(p["channel"] == "C0123ABCD" for p in posts)  # Glasgow has no message
    assert posts[0]["text"] == ("Leeds: 12 lines below reorder level. Details: "
                                "<http://127.0.0.1:24679/Operations/Stock.iox/r/Report/#Leeds|"
                                "http://127.0.0.1:24679/Operations/Stock.iox/r/Report/#Leeds>")
    assert all(c["headers"]["Authorization"] == "Bearer " + TOKEN and c["timeout"] for c in slack.calls)
    messages, sent = res.output(0), res.output(1)
    assert messages.columns.tolist() == ["Row", "Message", "AttachmentPath"] and len(messages) == 6
    assert sent.columns.tolist() == ["Row", "Action", "Channel", "Timestamp", "File ID"]
    assert sent["Action"].tolist() == ["postMessage"] * 2 + ["skip"] + ["postMessage"] * 3
    assert sent["Timestamp"].iloc[0] == "1741000000.000100"
    # every output value is a plain value: the original wrote Slack's whole reply (a Python dict) into a field
    for frame in (messages, sent):
        assert not frame.map(lambda v: isinstance(v, (dict, list))).any().any()
    assert res.final_message == "5 messages posted to C0123ABCD."


def test_links_end_at_the_first_space_and_special_characters_are_escaped(slack):
    # The original's link pattern ran on over spaces: 'see https://x.example/r for details' became one link
    # holding 'https://x.example/r for details'; and '<', '>', '&' were sent unescaped
    df = pd.DataFrame({"Message": ["See https://x.example/r for details.",
                                   "Margin < 5% & falling (see https://x.example/a_(b)).",
                                   "Already linked: <https://x.example/q|the report>, <@U0123> <!here>"]})
    run_block(HERE, df, SETTINGS).raise_for_error()
    assert [p["text"] for p in slack.posts()] == [
        "See <https://x.example/r|https://x.example/r> for details.",
        "Margin &lt; 5% &amp; falling (see <https://x.example/a_(b)|https://x.example/a_(b)>).",
        "Already linked: <https://x.example/q|the report>, <@U0123> <!here>"]


def test_integer_and_date_fields_with_missing_values(slack):
    # The original's fillna('') failed on these: "Invalid value '' for dtype 'Int64'"
    df = pd.DataFrame({"Message": ["a", "b"], "n": [1, None], "d": pd.to_datetime(["2025-03-01", None])})
    res = run_block(HERE, df, SETTINGS).raise_for_error()
    assert [p["text"] for p in slack.posts()] == ["a", "b"]


def test_attachment_upload_sends_the_three_requests(slack, tmp_path):
    pdf = tmp_path / "stock report.pdf"
    pdf.write_bytes(b"%PDF-1.4 stock report")
    df = pd.DataFrame({"Message": ["Weekly stock report"]})
    res = run_block(HERE, df, {**SETTINGS, "attachmentPath": str(pdf), "attachmentName": "Stock, week 12"})
    sent = res.raise_for_error().output(1)
    urls = [c["url"] for c in slack.calls]
    assert urls == ["https://slack.com/api/files.getUploadURLExternal",
                    "https://files.slack.com/upload/v1/CwABAAAAXwoAAZnoTEST",
                    "https://slack.com/api/files.completeUploadExternal"]
    assert slack.calls[0]["files"] == {"filename": (None, "stock report.pdf"), "length": (None, "21")}
    assert slack.calls[1]["data"] == b"%PDF-1.4 stock report" and "Authorization" not in slack.calls[1]["headers"]
    done = slack.calls[2]["files"]
    assert json.loads(done["files"][1]) == [{"id": "F0123FILE1", "title": "Stock, week 12"}]
    assert done["channel_id"] == (None, "C0123ABCD") and done["initial_comment"] == (None, "Weekly stock report")
    assert sent[["Action", "File ID"]].values.tolist() == [["upload_with_comment", "F0123FILE1"]]


def test_missing_attachment_stops_before_sending(slack, tmp_path):
    res = run_block(HERE, SAMPLE, {**SETTINGS, "attachmentPath": str(tmp_path / "nope.pdf")})
    assert res.status == "aborted" and "not found" in res.final_message and slack.calls == []


def test_slack_refusal_stops_with_a_hint_and_the_count(monkeypatch):
    fake = FakeSlack(fail="not_in_channel", fail_after=2)
    monkeypatch.setattr(requests, "post", fake)
    res = run_block(HERE, SAMPLE, SETTINGS)
    assert res.status == "aborted"
    assert res.final_message.startswith("Record 4 was not posted: chat.postMessage: not_in_channel (add the app")
    assert res.final_message.endswith("2 messages were posted before it.")
    for fail, words in (("invalid_auth", "xoxb-"), ("http", "HTTP 500"), ("network", "Failed to establish")):
        monkeypatch.setattr(requests, "post", FakeSlack(fail=fail))
        res = run_block(HERE, SAMPLE, SETTINGS)
        assert res.status == "aborted" and words in res.final_message and TOKEN not in res.final_message


def test_missing_settings_stop_before_sending(slack):
    for missing, words in (("authToken", "token"), ("channelID", "channel"), ("message", "field")):
        res = run_block(HERE, SAMPLE, {**SETTINGS, missing: None})
        assert res.status == "aborted" and words in res.final_message
    assert run_block(HERE, None, SETTINGS).status == "aborted"
    assert slack.calls == []


def test_empty_input(slack):
    df = pd.DataFrame({"Message": pd.Series([], dtype=object)})
    res = run_block(HERE, df, SETTINGS).raise_for_error()
    assert slack.calls == [] and len(res.output(0)) == 0 and len(res.output(1)) == 0
    assert res.output(1).columns.tolist() == ["Row", "Action", "Channel", "Timestamp", "File ID"]


def test_many_messages(slack):
    n = 2_000
    df = pd.DataFrame({"Message": [f"Alert {i}: https://x.example/{i}" for i in range(n)]})
    t0 = time.time()
    res = run_block(HERE, df, SETTINGS).raise_for_error()
    assert time.time() - t0 < 30 and len(slack.posts()) == n and len(res.output(1)) == n
