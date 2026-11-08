"""Tests for the Flipside block against an invented query result (tests/canned/query-result.json, written by
tests/make_canned.py). No test calls Flipside: the flipside SDK modules are replaced by fakes that answer like the
SDK (query() returns the first page, get_query_results() the next ones)."""
import json
import os
import sys
import types
from types import SimpleNamespace

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
with open(os.path.join(HERE, "tests", "canned", "query-result.json"), encoding="utf-8") as fh:
    RESULT = json.load(fh)
OPTS = {"key": "fs-test-key", "query": "SELECT block_date, chain, tx_count FROM demo.daily_activity"}


class FlipsideError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class ApiError(Exception):
    """Like the SDK's ApiError: the text is in str(e), there is no .message attribute."""

    def __init__(self, message):
        super().__init__(f"MethodValidationError: message={message}, code=-32000")


ERRORS = {n: type(n, (FlipsideError,), {}) for n in
          ("QueryRunExecutionError", "QueryRunCancelledError", "QueryRunRateLimitError", "QueryRunTimeoutError",
           "ServerError", "SDKError")}
ERRORS["ApiError"] = ApiError


def fake_sdk(calls, records=None, fail=None, columns=None):
    records = RESULT["records"] if records is None else records

    class Flipside:
        def __init__(self, api_key, *a, **kw):
            calls.append(("init", api_key))

        def query(self, sql, page_size=100000, page_number=1, **kw):
            calls.append(("query", sql, page_size, page_number, kw))
            if fail:
                raise fail
            start = (page_number - 1) * page_size
            return SimpleNamespace(query_id=RESULT["query_id"], records=records[start:start + page_size],
                                   columns=RESULT["columns"] if columns is None else columns)

        def get_query_results(self, query_id, page_number=1, page_size=100000):
            calls.append(("page", query_id, page_number, page_size))
            start = (page_number - 1) * page_size
            return SimpleNamespace(records=records[start:start + page_size])

    errors = types.ModuleType("flipside.errors")
    for name, cls in ERRORS.items():
        setattr(errors, name, cls)
    module = types.ModuleType("flipside")
    module.Flipside = Flipside
    module.errors = errors
    return module, errors


@pytest.fixture
def install(monkeypatch):
    def _install(**kw):
        calls = []
        module, errors = fake_sdk(calls, **kw)
        monkeypatch.setitem(sys.modules, "flipside", module)
        monkeypatch.setitem(sys.modules, "flipside.errors", errors)
        return calls
    return _install


def test_query_result(install):
    calls = install()
    res = run_block(HERE, None, OPTS).raise_for_error()
    out = res.output(0)
    assert len(out) == 60 and out.columns.tolist() == ["block_date", "chain", "tx_count", "active_addresses",
                                                       "avg_fee_usd"]
    assert out.groupby("chain").size().to_dict() == {"arbitrum": 30, "ethereum": 30}
    assert calls[0] == ("init", "fs-test-key")
    assert calls[1][1] == OPTS["query"] and calls[1][4]["max_age_minutes"] == 0
    assert res.final_message == "Retrieved 60 records."


def test_first_page_is_not_downloaded_twice(install):
    # The original read page 1 with query() and then again with get_query_results(page 1), and always asked
    # for one more page after the last
    calls = install()
    run_block(HERE, None, OPTS).raise_for_error()
    assert [c[0] for c in calls] == ["init", "query"]


def test_every_page_is_read(install):
    many = [dict(RESULT["records"][i % 60], __row_index=i) for i in range(25000)]
    calls = install(records=many)
    out = run_block(HERE, None, OPTS).raise_for_error().output(0)
    assert len(out) == 25000 and "__row_index" not in out.columns
    assert [c[2] for c in calls if c[0] == "page"] == [2, 3]


def test_result_without_row_index(install):
    # The original failed with KeyError when the records had no __row_index
    install(records=[{k: v for k, v in r.items() if k != "__row_index"} for r in RESULT["records"]])
    assert len(run_block(HERE, None, OPTS).raise_for_error().output(0)) == 60


def test_no_rows_keeps_the_columns(install):
    # The original wrote nothing, so downstream blocks lost their fields
    install(records=[])
    res = run_block(HERE, None, OPTS).raise_for_error()
    assert len(res.output(0)) == 0
    assert res.output(0).columns.tolist() == ["block_date", "chain", "tx_count", "active_addresses", "avg_fee_usd"]


@pytest.mark.parametrize("name,text", [("QueryRunExecutionError", "could not run the query"),
                                       ("QueryRunRateLimitError", "rate limited"),
                                       ("QueryRunTimeoutError", "longer than the specified timeout"),
                                       ("QueryRunCancelledError", "could not run the query"),
                                       ("ServerError", "server-side error"), ("SDKError", "API error"),
                                       ("ApiError", "API error")])
def test_sdk_errors_abort_with_a_message(install, name, text):
    install(fail=ERRORS[name]("details from Flipside"))
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and text in res.final_message and "details from Flipside" in res.final_message


def test_unreachable_service(install):
    install(fail=ConnectionError("Failed to resolve api-v2.flipsidecrypto.xyz"))
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and "Could not reach Flipside" in res.final_message


def test_missing_key_or_query(install):
    calls = install()
    res = run_block(HERE, None, {"query": OPTS["query"]})
    assert res.status == "aborted" and "API key" in res.final_message
    res = run_block(HERE, None, {"key": "fs-test-key", "query": "   "})
    assert res.status == "aborted" and "SQL query" in res.final_message
    assert calls == []
