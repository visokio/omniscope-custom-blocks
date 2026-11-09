"""Airtable block tests. No call reaches Airtable: a stand-in `requests` module returns the canned pages saved
beside this file (page-1.json, page-2.json, error-*.json) and records each request the block would send."""
import json
import os
import sys
import time
import types

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
TESTS = os.path.join(HERE, "tests")
PLACEHOLDER = os.path.join(HERE, "sample-data", "placeholder.csv")
OPTS = {"token": "patFAKE.token", "base_id": "appTEST0000000000", "table": "Bookings"}


def canned(name):
    with open(os.path.join(TESTS, name), encoding="utf-8") as fh:
        return json.load(fh)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeRequests(types.ModuleType):
    """Replaces the `requests` module: answers from a queue and records the requests."""

    class RequestException(IOError):
        pass

    def __init__(self, responses):
        super().__init__("requests")
        self.responses = list(responses)
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append({"url": url, "headers": dict(headers or {}), "params": dict(params or {}),
                           "timeout": timeout})
        nxt = self.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return FakeResponse(*nxt)


@pytest.fixture
def fake(monkeypatch):
    def install(*responses):
        mod = FakeRequests(responses)
        monkeypatch.setitem(sys.modules, "requests", mod)
        return mod
    monkeypatch.setattr(time, "sleep", lambda s: None)
    return install


def two_pages():
    return [(200, canned("page-1.json")), (200, canned("page-2.json"))]


def test_reads_every_page(fake):
    req = fake(*two_pages())
    out = run_block(HERE, None, OPTS).raise_for_error().output(0)
    assert len(out) == 12
    assert list(out.columns)[:4] == ["id", "Name", "Email", "Workshop"]
    assert out["id"].iloc[0] == "rec01AbCdEfGhIjK" and out["id"].iloc[-1] == "rec12AbCdEfGhIjK"
    # the second request carries the offset from the first page
    assert "offset" not in req.calls[0]["params"]
    assert req.calls[1]["params"]["offset"] == "itrPAGE2/rec07AbCdEfGhIjK"
    assert req.calls[0]["url"] == "https://api.airtable.com/v0/appTEST0000000000/Bookings"
    assert req.calls[0]["headers"] == {"Authorization": "Bearer patFAKE.token"}
    assert req.calls[0]["params"]["pageSize"] == 100
    assert req.calls[0]["timeout"]  # never waits for ever
    # lists and objects become JSON text; an unticked checkbox (left out by Airtable) is false
    assert out.loc[2, "Tags"] == '["weekend", "group"]'
    assert json.loads(out.loc[3, "Attachments"])[0]["filename"] == "form-4.pdf"
    assert out["Paid"].dtype == bool and out["Paid"].sum() == 8
    assert pd.isna(out.loc[10, "Seats"]) and out["Seats"].sum() == 20


def test_matches_the_placeholder_sample(fake):
    # sample-data/placeholder.csv is what the block outputs for the canned pages
    fake(*two_pages())
    out = run_block(HERE, None, OPTS).raise_for_error().output(0)
    expected = pd.read_csv(PLACEHOLDER)
    got = pd.read_csv(pd.io.common.StringIO(out.to_csv(index=False)))
    pd.testing.assert_frame_equal(got, expected)


def test_table_names_are_escaped_in_the_address(fake):
    # The original put the name into the URL as typed, so "Sales / 2026" became two path parts
    req = fake((200, {"records": []}))
    run_block(HERE, None, {**OPTS, "table": "Sales / 2026 #1"}).raise_for_error()
    assert req.calls[0]["url"].endswith("/appTEST0000000000/Sales%20%2F%202026%20%231")


def test_view_and_filter_formula_are_sent(fake):
    req = fake((200, canned("page-2.json")))
    opts = {**OPTS, "view": "Unpaid", "filter_formula": "{Paid} = FALSE()", "page_size": 25}
    run_block(HERE, None, opts).raise_for_error()
    assert req.calls[0]["params"] == {"pageSize": 25, "view": "Unpaid", "filterByFormula": "{Paid} = FALSE()"}


def test_empty_table_gives_an_empty_output(fake):
    # The original wrote no output at all, so the next block had nothing to read
    fake((200, {"records": []}))
    res = run_block(HERE, None, OPTS).raise_for_error()
    assert len(res.output(0)) == 0 and list(res.output(0).columns) == ["id"]
    assert "no records" in res.final_message


def test_a_table_field_called_id_is_kept(fake):
    # The original overwrote a field called "id" with the record ID
    fake((200, {"records": [{"id": "recA", "fields": {"id": 17, "Name": "x"}}]}))
    out = run_block(HERE, None, OPTS).raise_for_error().output(0)
    assert out.loc[0, "id"] == 17 and out.loc[0, "Airtable record ID"] == "recA"


def test_mixed_text_and_numbers_become_text(fake):
    recs = [{"id": "r1", "fields": {"Score": 3}}, {"id": "r2", "fields": {"Score": {"specialValue": "NaN"}}},
            {"id": "r3", "fields": {}}]
    fake((200, {"records": recs}))
    out = run_block(HERE, None, OPTS).raise_for_error().output(0)
    assert out["Score"].tolist()[:2] == ["3", '{"specialValue": "NaN"}'] and pd.isna(out["Score"].iloc[2])


def test_rate_limit_is_waited_out(fake):
    # The original aborted on the first 429
    req = fake((429, canned("error-429.json")), *two_pages())
    res = run_block(HERE, None, OPTS).raise_for_error()
    assert len(res.output(0)) == 12 and len(req.calls) == 3
    assert any("rate limit" in m for m in res.messages)


def test_errors_and_bad_options_abort_with_a_message(fake):
    fake((403, canned("error-403.json")))
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and "403" in res.final_message and "data.records:read" in res.final_message
    fake(FakeRequests.RequestException("connection refused"))
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and "Could not reach Airtable" in res.final_message
    req = fake()
    res = run_block(HERE, None, {**OPTS, "token": None})
    assert res.status == "aborted" and "token" in res.final_message and not req.calls
    # The original silently changed an out-of-range page size to 100
    res = run_block(HERE, None, {**OPTS, "page_size": 0})
    assert res.status == "aborted" and "Page size" in res.final_message


def test_many_pages(fake):
    pages = []
    for p in range(60):
        recs = [{"id": f"rec{p}_{i}", "fields": {"N": p * 100 + i, "Tags": ["a", "b"] if i % 2 else []}}
                for i in range(100)]
        pages.append((200, {"records": recs, **({"offset": f"o{p}"} if p < 59 else {})}))
    fake(*pages)
    t0 = time.time()
    out = run_block(HERE, None, OPTS).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert len(out) == 6000 and out["N"].tolist() == list(range(6000))
