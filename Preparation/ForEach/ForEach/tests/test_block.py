"""Tests for For Each (Separate Workflows). No Omniscope server is called: urllib3.PoolManager is replaced by a fake
that answers like a project's Workflow REST API (w/updateparams, w/execute, w/job/<id>/state) and records each
request, so the tests check the exact requests the block would send. What they cannot check: that a real server
accepts these requests, runs the other project and reports its state as documented."""
import json
import os
import time
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import urllib3

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "branches.csv")
URL = "http://127.0.0.1:24679/Reports/Branch report.iox/"
BASE = "http://127.0.0.1:24679/Reports/Branch%20report.iox/"
OPTS = {"Iox_File_Url": URL, "Parameters": ["Branch", "Quarter", "Minimum order"]}


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


# ------------------------------------------------------------------ normal runs

def test_sample_runs_the_project_once_per_record(serve):
    fake = serve()
    res = run_block(HERE, SAMPLE, OPTS).raise_for_error()
    updates = fake.calls("/w/updateparams")
    executes = fake.calls("/w/execute")
    assert len(updates) == 6 and len(executes) == 6
    assert updates[0]["url"] == BASE + "w/updateparams"
    assert updates[0]["body"] == {"updates": [{"name": "Branch", "value": "Leeds"},
                                              {"name": "Quarter", "value": "2025-Q1"},
                                              {"name": "Minimum order", "value": 250}]}
    assert executes[0]["body"] == {"blocks": [], "refreshFromSource": False, "cancelExisting": False}
    # parameters are set, then the run starts and is waited for, record after record
    kinds = [r["url"].rsplit("/", 1)[-1] for r in fake.requests]
    assert kinds[:4] == ["updateparams", "execute", "state", "state"]
    assert fake.requests[2]["url"] == BASE + "w/job/JOB_1/state"
    runs = res.output(0)
    assert list(runs.columns) == ["Run", "Branch", "Quarter", "Minimum order", "Result", "Job ID"]
    assert runs["Run"].tolist() == [1, 2, 3, 4, 5, 6]
    assert set(runs["Result"]) == {"COMPLETED"} and runs["Job ID"].tolist()[0] == "JOB_1"
    assert res.final_message == "6 runs, 6 completed."


def test_refresh_from_source_is_sent_as_a_json_boolean(serve):
    # The original sent the text "true" (and "none" when untouched) instead of a boolean
    fake = serve()
    run_block(HERE, SAMPLE, {**OPTS, "Refresh_From_Source": True}).raise_for_error()
    assert fake.calls("/w/execute")[0]["body"]["refreshFromSource"] is True
    fake = serve()
    run_block(HERE, SAMPLE, {**OPTS, "Refresh_From_Source": None}).raise_for_error()
    assert fake.calls("/w/execute")[0]["body"]["refreshFromSource"] is False


def test_blocks_list_drops_blank_names(serve):
    # The original sent [""] for an emptied option, which the server answers with BLOCKS_NOT_FOUND
    fake = serve()
    run_block(HERE, SAMPLE, {**OPTS, "Block_Names": ""}).raise_for_error()
    assert fake.calls("/w/execute")[0]["body"]["blocks"] == []
    fake = serve()
    run_block(HERE, SAMPLE, {**OPTS, "Block_Names": " Branch filter, PDF output ,"}).raise_for_error()
    assert fake.calls("/w/execute")[0]["body"]["blocks"] == ["Branch filter", "PDF output"]


def test_dates_missing_values_and_integers_become_valid_json(serve):
    # The original crashed on a date (Timestamp is not JSON serialisable) and sent NaN, which is not JSON
    df = pd.DataFrame({"Day": pd.to_datetime(["2025-03-01", "2025-03-02"]), "Limit": [5, None],
                       "Rate": [0.5, np.nan], "Flag": [True, False]})
    fake = serve()
    run_block(HERE, df, {**OPTS, "Parameters": ["Day", "Limit", "Rate", "Flag"]}).raise_for_error()
    raw = [r["raw"] for r in fake.calls("/w/updateparams")]
    assert "NaN" not in "".join(raw)
    first, second = [r["body"]["updates"] for r in fake.calls("/w/updateparams")]
    assert first == [{"name": "Day", "value": "2025-03-01T00:00:00+00:00"}, {"name": "Limit", "value": 5},
                     {"name": "Rate", "value": 0.5}, {"name": "Flag", "value": True}]
    assert [u["value"] for u in second] == ["2025-03-02T00:00:00+00:00", None, None, False]


def test_project_address_is_cut_back_and_encoded(serve):
    fake = serve()
    pasted = "http://127.0.0.1:24679/Reports/Branch report.iox/r/Report/#Summary"
    run_block(HERE, SAMPLE, {**OPTS, "Iox_File_Url": pasted}).raise_for_error()
    assert fake.requests[0]["url"] == BASE + "w/updateparams"
    fake = serve()
    run_block(HERE, SAMPLE, {**OPTS, "Iox_File_Url": "http://127.0.0.1:24679/Reports/Branch%20report.iox"}
              ).raise_for_error()
    assert fake.requests[0]["url"] == BASE + "w/updateparams"


def test_username_and_password_are_sent_with_basic_authentication(serve):
    fake = serve()
    run_block(HERE, SAMPLE, {**OPTS, "username": "scheduler", "password": "example-only"}).raise_for_error()
    assert fake.requests[0]["headers"]["authorization"] == urllib3.make_headers(
        basic_auth="scheduler:example-only")["authorization"]
    fake = serve()
    run_block(HERE, SAMPLE, OPTS).raise_for_error()
    assert "authorization" not in {k.lower() for k in fake.requests[0]["headers"]}


# ------------------------------------------------------------------ failures

def test_failed_run_stops_with_the_record_named(serve):
    fake = serve(job_states=[["COMPLETED"], ["RUNNING", "FAILED"], ["COMPLETED"]])
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted"
    assert "Run 2 (Branch = York, Quarter = 2025-Q1, Minimum order = 250) ended FAILED" in res.final_message
    assert len(fake.calls("/w/execute")) == 2


def test_carry_on_after_failed_runs_lists_them(serve):
    fake = serve(job_states=[["COMPLETED"], ["FAILED"], ["CANCELLED"], ["COMPLETED"], ["COMPLETED"],
                             ["COMPLETED"]])
    res = run_block(HERE, SAMPLE, {**OPTS, "ignore_errors": True}).raise_for_error()
    assert res.output(0)["Result"].tolist() == ["COMPLETED", "FAILED", "CANCELLED", "COMPLETED", "COMPLETED",
                                                "COMPLETED"]
    assert len(fake.calls("/w/execute")) == 6
    assert res.final_message == "6 runs, 4 completed, 2 failed."


def test_cancelled_run_is_not_restarted_forever(serve):
    # The original started a cancelled run again, without end, while the job kept being cancelled
    fake = serve(jobs=["CANCELLED"])
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted" and "ended CANCELLED" in res.final_message
    assert len(fake.calls("/w/execute")) == 1


def test_server_errors_give_the_servers_message(serve):
    serve(params=(401, None))
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted" and "HTTP 401" in res.final_message
    assert "Project parameters access via APIs" in res.final_message
    serve(params=(400, {"status": "FAIL", "errorType": "PARAM_NOT_FOUND",
                        "errorMessage": "Parameter 'Minimum order' not found"}))
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted" and "Parameter 'Minimum order' not found" in res.final_message
    serve(execute=[(404, {"errorType": "BLOCKS_NOT_FOUND",
                          "errorMessage": "One or more blocks could not be found in the workflow: PDF"})])
    res = run_block(HERE, SAMPLE, {**OPTS, "Block_Names": "PDF"})
    assert res.status == "aborted" and "could not be found in the workflow: PDF" in res.final_message
    serve(execute=[(401, None)])
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted" and "Workflow Execution via APIs" in res.final_message


def test_busy_project_is_waited_for_then_given_up(serve):
    busy = (409, {"errorType": "WORKFLOW_ALREADY_RUNNING", "errorMessage": "running"})
    fake = serve(execute=[busy, busy])
    run_block(HERE, SAMPLE, OPTS).raise_for_error()
    assert len(fake.calls("/w/execute")) == 8  # 2 refused, then 6 runs
    # The original retried for ever (a project pointed at itself never stops)
    fake = serve(execute=[busy] * 30000)
    res = run_block(HERE, SAMPLE, {**OPTS, "busy_wait_minutes": 0})
    assert res.status == "aborted" and "still busy after 0 minutes" in res.final_message
    assert len(fake.calls("/w/execute")) == 1


def test_run_stuck_in_the_queue_is_given_up(serve):
    serve(jobs=["QUEUED"])
    res = run_block(HERE, SAMPLE, {**OPTS, "busy_wait_minutes": 0})
    assert res.status == "aborted" and "Concurrent Workflow Jobs" in res.final_message


def test_unreachable_server_gives_a_message(monkeypatch):
    class Down:
        def __call__(self, *a, **k):
            return self

        def request(self, *a, **k):
            raise urllib3.exceptions.MaxRetryError(None, "/w/updateparams", "Connection refused")

    monkeypatch.setattr(urllib3, "PoolManager", Down())
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted" and res.final_message.startswith("Could not reach " + BASE)


# ------------------------------------------------------------------ options and inputs

def test_empty_input_runs_nothing(serve):
    fake = serve()
    df = pd.DataFrame({"Branch": pd.Series([], dtype=object), "Quarter": pd.Series([], dtype=object)})
    res = run_block(HERE, df, {**OPTS, "Parameters": ["Branch", "Quarter"]}).raise_for_error()
    assert fake.requests == []
    assert len(res.output(0)) == 0 and list(res.output(0).columns) == ["Run", "Branch", "Quarter", "Result",
                                                                       "Job ID"]
    assert res.final_message == "No records in the input: nothing was run."


def test_option_checks(serve):
    fake = serve()
    for options, words in [({**OPTS, "Iox_File_Url": None}, "Project address"),
                           ({**OPTS, "Iox_File_Url": "http://127.0.0.1:24679/Reports/"}, "ending in .iox"),
                           ({**OPTS, "Parameters": None}, "Choose the parameter fields"),
                           ({**OPTS, "Parameters": ["Branch", "Region"]}, "Not in the input: Region")]:
        res = run_block(HERE, SAMPLE, options)
        assert res.status == "aborted" and words in res.final_message, (options, res.final_message)
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and "Connect the records" in res.final_message
    assert fake.requests == []


def test_field_named_like_an_output_field(serve):
    serve()
    df = pd.DataFrame({"Result": ["a", "b"]})
    out = run_block(HERE, df, {**OPTS, "Parameters": ["Result"]}).raise_for_error().output(0)
    assert list(out.columns) == ["Run", "Result", "Result (For Each)", "Job ID"]


def test_many_records(serve):
    fake = serve(jobs=["COMPLETED"])
    n = 2000
    df = pd.DataFrame({"Branch": [f"B{i}" for i in range(n)], "Minimum order": np.arange(n)})
    started = time.perf_counter()
    res = run_block(HERE, df, {**OPTS, "Parameters": ["Branch", "Minimum order"]}).raise_for_error()
    assert len(res.output(0)) == n and len(fake.calls("/w/updateparams")) == n
    assert fake.calls("/w/updateparams")[-1]["body"]["updates"][1] == {"name": "Minimum order", "value": n - 1}
    assert time.perf_counter() - started < 20
