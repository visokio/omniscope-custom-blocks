"""Tests for Conditional Execution. No Omniscope server is called: urllib3.PoolManager is replaced by a fake that
answers like a project's Workflow REST API (w/execute) and records each request, so the tests check the exact
request the block would send, or that it sends none. What they cannot check: that a real server starts the blocks,
and how its cancelExisting and waitForIdle flags behave when the project is the one this block runs in."""
import json
import os
import time
from types import SimpleNamespace

import pytest
import urllib3

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
URL = "http://127.0.0.1:24679/Community/Blocks/Preparation/Conditional Execution/demo.iox/"
BASE = "http://127.0.0.1:24679/Community/Blocks/Preparation/Conditional%20Execution/demo.iox/"
OPTS = {"Iox_File_Url": URL, "Block_Names": "Stock levels, Reorder list", "execute": True}


class FakeOmniscope:
    """Answers like an Omniscope project's Workflow REST API, and records every request.

    ``jobs``: the states the job-state endpoint reports for each started run, in order (the last one repeats);
    ``execute``: answers to give to w/execute before the normal one, e.g. [(409, {...})];
    ``params``: answer to w/updateparams."""

    def __init__(self, jobs=("RUNNING", "COMPLETED"), execute=(), params=(200, {"status": "SUCCESS"}),
                 job_states=None):
        self.requests = []
        self.jobs = list(jobs)
        self.job_states = job_states  # optional: one list of states per run
        self.execute_answers = list(execute)
        self.params = params
        self.started = 0
        self.polls = {}

    # urllib3.PoolManager() is replaced by a function returning this object
    def __call__(self, *args, **kwargs):
        return self

    def request(self, method, url, headers=None, body=None, **kwargs):
        if len(self.requests) > 20000:
            raise RuntimeError("runaway: more than 20000 requests")
        payload = json.loads(body) if body else None
        self.requests.append({"method": method, "url": url, "headers": dict(headers or {}), "body": payload,
                              "raw": body})
        if url.endswith("/w/updateparams"):
            return answer(*self.params)
        if url.endswith("/w/execute"):
            if self.execute_answers:
                return answer(*self.execute_answers.pop(0))
            self.started += 1
            return answer(200, {"jobId": f"JOB_{self.started}"})
        if "/w/job/" in url and url.endswith("/state"):
            job = url.split("/w/job/")[1].split("/")[0]
            n = self.polls.get(job, 0)
            self.polls[job] = n + 1
            states = self.jobs if self.job_states is None else self.job_states[int(job.split("_")[1]) - 1]
            return answer(200, {"jobState": states[min(n, len(states) - 1)]})
        return answer(404, {})

    def calls(self, endpoint):
        return [r for r in self.requests if r["url"].endswith(endpoint)]


def answer(status, body):
    return SimpleNamespace(status=status, data=json.dumps(body).encode("utf-8") if body is not None else b"")


@pytest.fixture
def serve(monkeypatch):
    """serve(**kwargs) installs a FakeOmniscope as urllib3's PoolManager and returns it; time.sleep does nothing."""
    monkeypatch.setattr(time, "sleep", lambda seconds: None)

    def install(**kwargs):
        fake = FakeOmniscope(**kwargs)
        monkeypatch.setattr(urllib3, "PoolManager", fake)
        return fake

    return install


def test_on_starts_the_listed_blocks_once(serve):
    fake = serve()
    res = run_block(HERE, None, OPTS).raise_for_error()
    assert len(fake.requests) == 1
    call = fake.requests[0]
    assert call["method"] == "POST" and call["url"] == BASE + "w/execute"
    assert call["body"] == {"blocks": ["Stock levels", "Reorder list"], "refreshFromSource": False,
                            "cancelExisting": True, "waitForIdle": False}
    assert res.final_message == ("Started Stock levels, Reorder list (job JOB_1). This block does not wait for them "
                                 "to finish.")
    assert res.outputs == {}


def test_off_sends_nothing(serve):
    fake = serve()
    res = run_block(HERE, None, {**OPTS, "execute": False}).raise_for_error()
    assert fake.requests == [] and res.final_message == "Run the blocks is off: nothing was started."


def test_option_linked_to_a_text_parameter(serve):
    fake = serve()
    run_block(HERE, None, {**OPTS, "execute": "true"}).raise_for_error()
    assert len(fake.requests) == 1
    fake = serve()
    run_block(HERE, None, {**OPTS, "execute": "false"}).raise_for_error()
    assert fake.requests == []


def test_refresh_from_source_is_a_json_boolean(serve):
    # The original sent null when the option was untouched
    fake = serve()
    run_block(HERE, None, {**OPTS, "Refresh_From_Source": None}).raise_for_error()
    assert fake.requests[0]["body"]["refreshFromSource"] is False
    fake = serve()
    run_block(HERE, None, {**OPTS, "Refresh_From_Source": True}).raise_for_error()
    assert fake.requests[0]["body"]["refreshFromSource"] is True


def test_refused_request_is_reported_not_announced_as_started(serve):
    # The original never read the answer and always said "Workflow execution enqueued."
    serve(execute=[(404, {"errorType": "BLOCKS_NOT_FOUND",
                          "errorMessage": "One or more blocks could not be found in the workflow: Reorder list"})])
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and "could not be found in the workflow: Reorder list" in res.final_message
    serve(execute=[(401, None)])
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and "Workflow Execution via APIs" in res.final_message
    serve(execute=[(500, None)])
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and "HTTP 500" in res.final_message


def test_unreachable_server_gives_a_message(monkeypatch):
    class Down:
        def __call__(self, *a, **k):
            return self

        def request(self, *a, **k):
            raise urllib3.exceptions.MaxRetryError(None, "/w/execute", "Connection refused")

    monkeypatch.setattr(urllib3, "PoolManager", Down())
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and res.final_message.startswith("Could not reach " + BASE)


def test_block_list_is_required_and_blank_names_dropped(serve):
    # The original sent [""] for an empty option (BLOCKS_NOT_FOUND, reported as "enqueued")
    fake = serve()
    for blocks in ["", " , ", None]:
        res = run_block(HERE, None, {**OPTS, "Block_Names": blocks})
        assert res.status == "aborted" and "List the blocks to run" in res.final_message
    assert fake.requests == []
    run_block(HERE, None, {**OPTS, "Block_Names": "Reorder list,"}).raise_for_error()
    assert fake.requests[0]["body"]["blocks"] == ["Reorder list"]


def test_address_checks_and_credentials(serve):
    fake = serve()
    for bad in ["", None, "http://127.0.0.1:24679/Community/"]:
        res = run_block(HERE, None, {**OPTS, "Iox_File_Url": bad})
        assert res.status == "aborted" and res.final_message.startswith("Project address:")
    assert fake.requests == []
    run_block(HERE, None, {**OPTS, "Iox_File_Url": URL + "r/Report/#Stock", "username": "ops",
                           "password": "example-only"}).raise_for_error()
    assert fake.requests[0]["url"] == BASE + "w/execute"
    assert fake.requests[0]["headers"]["authorization"] == urllib3.make_headers(basic_auth="ops:example-only")["authorization"]


def test_an_input_is_ignored(serve):
    fake = serve()
    run_block(HERE, os.path.join(HERE, "sample-data", "stock-levels.csv"), OPTS).raise_for_error()
    assert len(fake.requests) == 1


def test_placeholder_is_the_reorder_list_the_started_run_builds():
    # The block has no output. The demo shows sample-data/placeholder.csv: the Reorder list that the run it starts
    # rebuilds (the Record filter In stock < Reorder level on the sample stock file).
    import pandas as pd
    stock = pd.read_csv(os.path.join(HERE, "sample-data", "stock-levels.csv"))
    expected = stock[stock["In stock"] < stock["Reorder level"]].reset_index(drop=True)
    placeholder = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"))
    pd.testing.assert_frame_equal(placeholder, expected)
    assert placeholder["SKU"].tolist() == ["GP-101", "CP-201", "TL-301", "HS-401"]
