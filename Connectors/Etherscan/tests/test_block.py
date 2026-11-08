"""Tests for the Etherscan block against canned Etherscan API V2 responses (tests/canned/, written by
tests/make_canned.py). No test calls Etherscan: requests.Session.request is replaced by a fake."""
import json
import os
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
SAMPLE = pd.read_csv(os.path.join(HERE, "sample-data", "addresses.csv"))
KEY = {"apikey": "TESTKEY123"}
V2 = "https://api.etherscan.io/v2/api"


def canned(name):
    with open(os.path.join(CANNED, name), encoding="utf-8") as fh:
        return json.load(fh)


def response(status, body):
    r = requests.Response()
    r.status_code = status
    r._content = json.dumps(body).encode("utf-8")
    r.headers["Content-Type"] = "application/json"
    return r


class FakeEtherscan:
    """Answers like Etherscan API V2 from the canned files, and records every request."""

    def __init__(self, txlists=None, script=None):
        self.calls = []
        self.txlists = txlists or {}
        self.script = list(script or [])  # responses to give first, in order

    def __call__(self, session, method, url, params=None, **kw):
        params = dict(params or {})
        self.calls.append({"method": method, "url": url, "params": params})
        if self.script:
            return self.script.pop(0)
        if url != V2:
            return response(200, {"status": "0", "message": "NOTOK", "result": "You are using a deprecated V1 "
                                  "endpoint, switch to Etherscan API V2 using https://docs.etherscan.io/v2-migration"})
        if params.get("action") == "balancemulti":
            known = {r["account"]: r["balance"] for r in canned("balancemulti.json")["result"]}
            asked = params["address"].split(",")
            return response(200, {"status": "1", "message": "OK",
                                  "result": [{"account": a, "balance": known.get(a.lower(), "1000000000000000000")}
                                             for a in asked]})
        if params.get("action") == "txlist":
            a = params["address"].lower()
            if a in self.txlists:
                start, n = int(params.get("startblock", 0)), int(params["offset"])
                rows = [t for t in self.txlists[a] if int(t["blockNumber"]) >= start][:n]
                return response(200, {"status": "1", "message": "OK", "result": rows})
            path = os.path.join(CANNED, f"txlist-{a}.json")
            if os.path.exists(path):
                return response(200, canned(f"txlist-{a}.json"))
            return response(200, {"status": "0", "message": "No transactions found", "result": []})
        return response(200, {"status": "0", "message": "NOTOK", "result": "Error! Missing Or invalid Action name"})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def es(monkeypatch):
    return install(monkeypatch, FakeEtherscan())


def run(df, **options):
    return run_block(HERE, [df], {**KEY, "address": "Address", **options})


def test_balances_of_the_sample(es):
    res = run(SAMPLE).raise_for_error()
    out = res.output(0)
    assert out.columns.tolist() == ["Account", "Balance", "Balance (wei)"]
    assert out["Account"].tolist() == SAMPLE["Address"].tolist()
    assert out["Balance"].tolist() == [184.25, 12.75033, 4.1, 0.0, 902.5]
    assert out["Balance (wei)"].iloc[0] == "184250000000000000000"
    assert str(out["Balance"].dtype) == "float64"
    assert res.final_message == "Balances of 5 address(es) on chain 1."


def test_requests_use_api_v2_with_chain_id(es):
    run(SAMPLE).raise_for_error()
    (call,) = es.calls
    assert call["url"] == V2
    p = call["params"]
    assert p["chainid"] == "1" and p["module"] == "account" and p["action"] == "balancemulti"
    assert p["address"].split(",") == SAMPLE["Address"].tolist() and p["apikey"] == "TESTKEY123"


def test_v1_endpoint_is_not_used(es):
    # The original block called the V1 endpoint (through the etherscan package), which Etherscan shut down
    # in August 2025: it now answers "You are using a deprecated V1 endpoint".
    run(SAMPLE, method="get_transactions_by_address").raise_for_error()
    assert es.calls and all(c["url"] == V2 for c in es.calls)


def test_other_chain(es):
    run(SAMPLE, chainid=" 8453 ").raise_for_error()
    assert es.calls[0]["params"]["chainid"] == "8453"


def test_bad_chain_id_aborts(es):
    res = run(SAMPLE, chainid="Ethereum")
    assert res.status == "aborted" and "Chain ID must be a number" in res.final_message and es.calls == []


def test_transactions_of_the_sample(es):
    res = run(SAMPLE, method="get_transactions_by_address").raise_for_error()
    out = res.output(0)
    assert len(out) == 31 + 24 + 12 + 0 + 3
    assert out.columns[:6].tolist() == ["Account", "Time", "Amount", "blockNumber", "timeStamp", "hash"]
    assert out.groupby("Account").size().to_dict() == {
        SAMPLE["Address"][0]: 31, SAMPLE["Address"][1]: 24, SAMPLE["Address"][2]: 12, SAMPLE["Address"][4]: 3}
    assert str(out["Time"].dt.tz) == "UTC" and out["Time"].min() >= pd.Timestamp("2025-01-01", tz="UTC")
    assert str(out["blockNumber"].dtype) == "Int64" and str(out["Amount"].dtype) == "float64"
    first = out.iloc[0]
    assert first["Amount"] == int(first["value"]) / 10 ** 18
    # each address is either the sender or the receiver of its transactions
    assert ((out["from"] == out["Account"]) | (out["to"] == out["Account"])).all()
    assert len([c for c in es.calls if c["params"]["action"] == "txlist"]) == 5
    assert res.final_message == "70 transactions of 5 address(es) on chain 1."


def test_more_than_twenty_addresses_are_batched(es):
    df = pd.DataFrame({"Address": ["0x" + f"{i:040x}" for i in range(1, 46)]})
    out = run(df).raise_for_error().output(0)
    assert len(out) == 45 and out["Balance"].eq(1.0).all()
    assert [len(c["params"]["address"].split(",")) for c in es.calls] == [20, 20, 5]


def test_values_that_are_not_addresses_are_skipped(es):
    a = SAMPLE["Address"].tolist()
    df = pd.DataFrame({"Address": [a[0], "  " + a[1].upper().replace("0X", "0x") + " ", a[0], None, "", "vitalik.eth",
                                   "0x1234"]})
    res = run(df).raise_for_error()
    assert len(res.output(0)) == 2 and res.output(0)["Balance"].tolist()[0] == 184.25
    assert "Skipped 2 value(s) that are not addresses, such as 'vitalik.eth'" in res.final_message


def test_refused_key_aborts_with_etherscan_message(monkeypatch):
    install(monkeypatch, FakeEtherscan(script=[response(200, {"status": "0", "message": "NOTOK",
                                                              "result": "Invalid API Key (#err2)|"})]))
    res = run(SAMPLE)
    assert res.status == "aborted" and "Invalid API Key" in res.final_message


def test_rate_limit_is_retried(monkeypatch):
    limited = response(200, {"status": "0", "message": "NOTOK", "result": "Max calls per sec rate limit reached (3/sec)"})
    fake = install(monkeypatch, FakeEtherscan(script=[limited, limited]))
    out = run(SAMPLE).raise_for_error().output(0)
    assert len(out) == 5 and len(fake.calls) == 3


def test_http_error_does_not_show_the_key(monkeypatch):
    install(monkeypatch, FakeEtherscan(script=[response(503, {"error": "unavailable"})]))
    res = run(SAMPLE)
    assert res.status == "aborted" and "HTTP 503" in res.final_message and "TESTKEY123" not in res.final_message


def test_more_than_10000_transactions_are_paged_by_block(monkeypatch):
    a = "0x" + "ab" * 20
    txs = [{"blockNumber": str(1000 + i // 3), "timeStamp": str(1735700000 + i), "hash": f"0x{i:064x}",
            "from": a, "to": "0x" + "cd" * 20, "value": "1000000000000000000", "isError": "0"} for i in range(23456)]
    fake = install(monkeypatch, FakeEtherscan(txlists={a: txs}))
    out = run(pd.DataFrame({"Address": [a]}), method="get_transactions_by_address").raise_for_error().output(0)
    assert len(out) == 23456 and out["hash"].is_unique
    starts = [int(c["params"]["startblock"]) for c in fake.calls]
    assert len(starts) == 3 and starts[0] == 0 and starts[1] > 0 and starts[2] > starts[1]
    assert out["Amount"].sum() == pytest.approx(23456.0)


def test_empty_input_gives_empty_output_with_fields(es):
    empty = SAMPLE.iloc[0:0]
    b = run(empty).raise_for_error().output(0)
    t = run(empty, method="get_transactions_by_address").raise_for_error().output(0)
    assert len(b) == 0 and b.columns.tolist() == ["Account", "Balance", "Balance (wei)"]
    assert len(t) == 0 and "Time" in t.columns and "hash" in t.columns
    assert es.calls == []


def test_wrong_types_and_missing_choices(es):
    numbers = pd.DataFrame({"Address": [1, 2, 3]})
    res = run(numbers).raise_for_error()
    assert len(res.output(0)) == 0 and "Skipped 3" in res.final_message
    assert run_block(HERE, None, {**KEY, "address": "Address"}).status == "aborted"
    assert "Address field" in run_block(HERE, [SAMPLE], KEY).final_message
    res = run_block(HERE, [SAMPLE], {"address": "Address"})
    assert res.status == "aborted" and "API key" in res.final_message
