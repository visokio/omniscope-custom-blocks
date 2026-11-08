"""Tests for the Dune block against a canned Dune result (tests/canned/results.json, written by
tests/make_canned.py). No test calls Dune: requests.Session.request is replaced by a fake that answers the
execute, status and results endpoints, and serves results in pages the way Dune does (next_uri)."""
import copy
import json
import os
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
BASE = "https://api.dune.com/api/v1"
with open(os.path.join(HERE, "tests", "canned", "results.json"), encoding="utf-8") as fh:
    RESULT = json.load(fh)
EXEC_ID = RESULT["execution_id"]
AUTH = {"duneApiKey": "dune-test-key", "queryId": "4100217"}


def response(status, body):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body).encode("utf-8")
    r.headers["Content-Type"] = "application/json"
    return r


class FakeDune:
    """Answers like api.dune.com. `states` is the sequence of states the status endpoint reports."""

    def __init__(self, result=None, states=("QUERY_STATE_PENDING", "QUERY_STATE_EXECUTING", "QUERY_STATE_COMPLETED"),
                 page=50, latest_status=200, error=None):
        self.calls = []
        self.result = result or RESULT
        self.states = list(states)
        self.page = page  # the most rows the fake returns per page, whatever limit is asked for
        self.latest_status = latest_status
        self.error = error

    def page_of(self, url, params):
        params = dict(params or {})
        if "?" in url:
            url, query = url.split("?", 1)
            params.update(dict(p.split("=", 1) for p in query.split("&")))
        offset, limit = int(params.get("offset", 0)), min(int(params.get("limit", 10 ** 9)), self.page)
        body = copy.deepcopy(self.result)
        rows = body["result"]["rows"]
        body["result"]["rows"] = rows[offset:offset + limit]
        body["result"]["metadata"]["row_count"] = len(body["result"]["rows"])
        if offset + limit < len(rows):
            body["next_offset"] = offset + limit
            body["next_uri"] = f"{url}?offset={offset + limit}&limit={limit}"
        return response(200, body)

    def __call__(self, session, method, url, params=None, json=None, headers=None, **kw):
        merged = requests.structures.CaseInsensitiveDict(session.headers)
        merged.update(headers or {})
        key = merged.get("X-Dune-Api-Key")
        method = method.upper()
        self.calls.append({"method": method, "url": url, "params": dict(params or {}), "json": json, "key": key})
        if key != "dune-test-key":
            return response(401, {"error": "invalid API Key"})
        if method == "POST" and url == f"{BASE}/query/4100217/execute":
            return response(200, {"execution_id": EXEC_ID, "state": "QUERY_STATE_PENDING"})
        if url == f"{BASE}/execution/{EXEC_ID}/status":
            state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
            body = {"execution_id": EXEC_ID, "query_id": 4100217, "state": state,
                    "is_execution_finished": state not in ("QUERY_STATE_PENDING", "QUERY_STATE_EXECUTING")}
            if self.error and state == "QUERY_STATE_FAILED":
                body["error"] = self.error
            return response(200, body)
        if url.startswith(f"{BASE}/execution/{EXEC_ID}/results"):
            return self.page_of(url, params)
        if url.startswith(f"{BASE}/query/4100217/results"):
            if self.latest_status != 200:
                return response(self.latest_status, {"error": "Query result not found"})
            return self.page_of(url, params)
        return response(404, {"error": f"not found: {url}"})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def dune(monkeypatch):
    return install(monkeypatch, FakeDune())


def test_latest_result_every_page_and_typed(dune):
    res = run_block(HERE, None, AUTH).raise_for_error()
    rows = res.output(1)
    assert len(rows) == 120
    assert rows.columns.tolist() == ["day", "chain", "trades", "volume_usd", "is_weekend", "top_pair",
                                     "largest_trade_wei", "venues"]
    assert str(rows["day"].dt.tz) == "UTC" and rows["day"].iloc[0] == pd.Timestamp("2026-09-01", tz="UTC")
    assert str(rows["trades"].dtype) == "Int64" and str(rows["volume_usd"].dtype) == "float64"
    assert str(rows["is_weekend"].dtype) == "boolean" and rows["is_weekend"].sum() == 32  # 8 weekend days x 4
    assert rows["largest_trade_wei"].iloc[0] == RESULT["result"]["rows"][0]["largest_trade_wei"]
    assert json.loads(rows["venues"].iloc[0]) == RESULT["result"]["rows"][0]["venues"]
    assert pd.isna(rows["volume_usd"].iloc[-1])
    assert rows.groupby("chain").size().to_dict() == {"arbitrum": 30, "base": 30, "ethereum": 30, "polygon": 30}
    assert res.final_message == "Query 4100217: 120 rows, 8 columns."


def test_pages_follow_next_uri(dune):
    # The original read only the first page Dune returned
    run_block(HERE, None, AUTH).raise_for_error()
    urls = [c["url"] for c in dune.calls]
    assert urls[0] == f"{BASE}/query/4100217/results" and dune.calls[0]["params"]["limit"] == 25000
    assert urls[1:] == [f"{BASE}/query/4100217/results?offset={o}&limit=50" for o in (50, 100)]
    assert all(c["key"] == "dune-test-key" for c in dune.calls)


def test_execution_output_is_one_tidy_record(dune):
    ex = run_block(HERE, None, AUTH).raise_for_error().output(0)
    assert ex.columns.tolist() == ["Execution ID", "Query ID", "State", "Submitted", "Started", "Ended", "Expires",
                                   "Rows"]
    assert len(ex) == 1 and ex["Rows"].iloc[0] == 120 and ex["Query ID"].iloc[0] == 4100217
    assert ex["State"].iloc[0] == "QUERY_STATE_COMPLETED"
    assert ex["Ended"].iloc[0] == pd.Timestamp("2026-10-01T06:00:41.906Z")
    for c in ex.columns:  # no list or dict values (the original put the whole result in one record)
        assert not ex[c].map(lambda v: isinstance(v, (list, dict))).any(), c


def test_execute_waits_then_reads_the_execution(dune):
    res = run_block(HERE, None, {**AUTH, "mode": "execAndRetrieve"}).raise_for_error()
    assert len(res.output(1)) == 120
    post = dune.calls[0]
    assert post["method"] == "POST" and post["url"] == f"{BASE}/query/4100217/execute"
    assert post["json"] == {"performance": "medium"}
    statuses = [c for c in dune.calls if c["url"].endswith("/status")]
    assert len(statuses) == 3
    assert dune.calls[4]["url"] == f"{BASE}/execution/{EXEC_ID}/results"


def test_engine_size(dune):
    run_block(HERE, None, {**AUTH, "mode": "execAndRetrieve", "performance": "large"}).raise_for_error()
    assert dune.calls[0]["json"] == {"performance": "large"}


@pytest.mark.parametrize("state", ["QUERY_STATE_FAILED", "QUERY_STATE_CANCELED", "QUERY_STATE_EXPIRED"])
def test_failed_execution_stops_with_dunes_message(monkeypatch, state):
    # The original polled forever: it only stopped on QUERY_STATE_COMPLETED
    fake = install(monkeypatch, FakeDune(states=["QUERY_STATE_EXECUTING", state],
                                         error={"type": "FAILED_TYPE_EXECUTION_FAILED",
                                                "message": "line 3:8: Column 'amount_usd' cannot be resolved"}))
    res = run_block(HERE, None, {**AUTH, "mode": "execAndRetrieve"})
    assert res.status == "aborted"
    assert state.replace("QUERY_STATE_", "").lower() in res.final_message
    if state == "QUERY_STATE_FAILED":
        assert "cannot be resolved" in res.final_message
    assert len([c for c in fake.calls if c["url"].endswith("/status")]) == 2


def test_partial_result_is_kept_and_said(monkeypatch):
    partial = copy.deepcopy(RESULT)
    partial["state"] = "QUERY_STATE_COMPLETED_PARTIAL"
    partial["result"]["rows"] = partial["result"]["rows"][:40]
    install(monkeypatch, FakeDune(result=partial, states=["QUERY_STATE_COMPLETED_PARTIAL"]))
    res = run_block(HERE, None, {**AUTH, "mode": "execAndRetrieve"}).raise_for_error()
    assert len(res.output(1)) == 40 and "partial result" in res.final_message


def test_query_id_from_an_address(dune):
    run_block(HERE, None, {**AUTH, "queryId": " https://dune.com/queries/4100217/6512345 "}).raise_for_error()
    assert dune.calls[0]["url"] == f"{BASE}/query/4100217/results"
    res = run_block(HERE, None, {**AUTH, "queryId": "daily volume"})
    assert res.status == "aborted" and "Query ID must be a number" in res.final_message


def test_refused_key_and_missing_result(monkeypatch):
    install(monkeypatch, FakeDune())
    res = run_block(HERE, None, {**AUTH, "duneApiKey": "wrong"})
    assert res.status == "aborted" and res.final_message == "Dune refused the request (HTTP 401): invalid API Key"
    install(monkeypatch, FakeDune(latest_status=404))
    res = run_block(HERE, None, AUTH)
    assert res.status == "aborted" and "Execute and retrieve latest results" in res.final_message
    assert run_block(HERE, None, {"queryId": "4100217"}).final_message.startswith("Enter your Dune API key")


def test_empty_result_keeps_the_columns(monkeypatch):
    empty = copy.deepcopy(RESULT)
    empty["result"]["rows"] = []
    empty["result"]["metadata"]["total_row_count"] = 0
    install(monkeypatch, FakeDune(result=empty))
    res = run_block(HERE, None, AUTH).raise_for_error()
    rows = res.output(1)
    assert len(rows) == 0 and rows.columns.tolist()[:3] == ["day", "chain", "trades"]
    assert str(rows["trades"].dtype) == "Int64" and res.output(0)["Rows"].iloc[0] == 0


def test_unexpected_values_never_break_the_types(monkeypatch):
    odd = copy.deepcopy(RESULT)
    r = odd["result"]["rows"]
    r[0]["trades"], r[1]["day"], r[2]["largest_trade_wei"], r[3]["is_weekend"] = "n/a", None, 10 ** 30, None
    r[4]["extra"] = {"note": "not in the metadata"}
    odd["result"]["metadata"]["column_types"] = odd["result"]["metadata"]["column_types"][:-1]  # venues untyped
    install(monkeypatch, FakeDune(result=odd))
    rows = run_block(HERE, None, AUTH).raise_for_error().output(1)
    assert pd.isna(rows["trades"].iloc[0]) and pd.isna(rows["day"].iloc[1])
    assert rows["largest_trade_wei"].iloc[2] == str(10 ** 30) and pd.isna(rows["is_weekend"].iloc[3])
    assert rows.columns[-1] == "extra" and rows["extra"].iloc[4] == '{"note": "not in the metadata"}'
    assert rows["venues"].map(lambda v: isinstance(v, str)).all()


def test_large_result(monkeypatch):
    big = copy.deepcopy(RESULT)
    base_rows = big["result"]["rows"]
    big["result"]["rows"] = [dict(base_rows[i % 120], trades=i) for i in range(100000)]
    fake = install(monkeypatch, FakeDune(result=big, page=25000))
    rows = run_block(HERE, None, AUTH).raise_for_error().output(1)
    assert len(rows) == 100000 and rows["trades"].tolist()[-1] == 99999
    assert len(fake.calls) == 4
