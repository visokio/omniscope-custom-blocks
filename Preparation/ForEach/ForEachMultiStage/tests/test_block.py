"""Tests for For Each Multi Stage. No Omniscope server is called: urllib3.PoolManager is replaced by a fake that
answers like a project's Workflow REST API (w/updateparams, w/execute, w/job/<id>/state) and records each request,
so the tests check the exact requests the block would send, and in which order. What they cannot check: that a
real server accepts these requests and runs the other project's blocks as documented."""
import json
import os
import time
from types import SimpleNamespace

import pandas as pd
import pytest
import urllib3

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "regions.csv")
BASE = "http://127.0.0.1:24679/Sales/Regional%20pack.iox/"
OPTS = {"Iox_File_Url": "http://127.0.0.1:24679/Sales/Regional pack.iox/", "Parameters": ["Region", "Report title"],
        "Block_Names_Before": "Sales database", "Refresh_From_Source_Before": True,
        "Block_Names": "Region filter, Summary", "Block_Names2": "Region PDF", "Block_Names3": ""}


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


def sequence(fake):
    """The requests as short labels: 'params Region=..', 'run [blocks] refresh', 'state'."""
    out = []
    for r in fake.requests:
        if r["url"].endswith("/w/updateparams"):
            out.append("params " + ", ".join(f"{u['name']}={u['value']}" for u in r["body"]["updates"]))
        elif r["url"].endswith("/w/execute"):
            out.append("run " + "+".join(r["body"]["blocks"]) + (" refresh" if r["body"]["refreshFromSource"] else ""))
    return out


def test_sample_runs_before_stage_once_then_two_stages_per_record(serve):
    fake = serve(jobs=["COMPLETED"])
    res = run_block(HERE, SAMPLE, OPTS).raise_for_error()
    seq = sequence(fake)
    assert seq[:4] == ["run Sales database refresh",
                       "params Region=North East, Report title=North East: weekly sales",
                       "run Region filter+Summary", "run Region PDF"]
    assert len(seq) == 1 + 5 * 3
    assert all(r["url"].startswith(BASE) for r in fake.requests)
    assert fake.calls("/w/execute")[1]["body"] == {"blocks": ["Region filter", "Summary"],
                                                   "refreshFromSource": False, "cancelExisting": False}
    out = res.output(0)
    assert list(out.columns) == ["Pass", "Region", "Report title", "Result", "Failed at stage", "Job IDs"]
    assert out["Pass"].tolist() == [1, 2, 3, 4, 5] and set(out["Result"]) == {"COMPLETED"}
    assert out["Job IDs"].tolist()[0] == "JOB_2, JOB_3" and out["Failed at stage"].isna().all()
    assert res.final_message == "5 passes, 5 completed."


def test_each_stage_waits_for_the_previous_one(serve):
    fake = serve(jobs=["QUEUED", "RUNNING", "BLOCKED", "COMPLETED"])
    run_block(HERE, SAMPLE, OPTS).raise_for_error()
    labels = [r["url"].rsplit("/", 1)[-1] for r in fake.requests]
    # before stage: execute + 4 polls, then params, execute + 4 polls, execute + 4 polls, ...
    assert labels[:5] == ["execute", "state", "state", "state", "state"]
    assert labels[5:16] == ["updateparams"] + ["execute"] + ["state"] * 4 + ["execute"] + ["state"] * 4


def test_refresh_flags_are_json_booleans_per_stage(serve):
    # The original sent the text "true"/"false"/"none"
    fake = serve(jobs=["COMPLETED"])
    run_block(HERE, SAMPLE, {**OPTS, "Refresh_From_Source": True, "Refresh_From_Source2": None,
                             "Block_Names3": "Archive", "Refresh_From_Source3": True}).raise_for_error()
    flags = [(r["body"]["blocks"], r["body"]["refreshFromSource"]) for r in fake.calls("/w/execute")[:4]]
    assert flags == [(["Sales database"], True), (["Region filter", "Summary"], True), (["Region PDF"], False),
                     (["Archive"], True)]


def test_empty_stage_options_are_skipped_and_stage_1_defaults_to_all_blocks(serve):
    # The original sent [""] for an emptied option: BLOCKS_NOT_FOUND, or an extra run for stages 2 and 3
    fake = serve(jobs=["COMPLETED"])
    run_block(HERE, SAMPLE, {**OPTS, "Block_Names_Before": "", "Block_Names": "", "Block_Names2": " , ",
                             "Block_Names3": None}).raise_for_error()
    assert sequence(fake)[:3] == ["params Region=North East, Report title=North East: weekly sales", "run ",
                                  "params Region=North West, Report title=North West: weekly sales"]
    assert [r["body"]["blocks"] for r in fake.calls("/w/execute")] == [[]] * 5


def test_failure_in_a_stage_stops_with_the_pass_and_stage_named(serve):
    # job 1 = before stage, jobs 2-3 = pass 1, job 4 = pass 2 stage 1, job 5 = pass 2 stage 2 fails
    fake = serve(job_states=[["COMPLETED"]] * 4 + [["FAILED"]] + [["COMPLETED"]] * 20)
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted"
    assert res.final_message.startswith("Pass 2 (Region = North West, Report title = North West: weekly sales) "
                                        "ended FAILED at stage 2")
    assert len(fake.calls("/w/execute")) == 5


def test_carry_on_skips_the_rest_of_a_failed_pass(serve):
    fake = serve(job_states=[["COMPLETED"]] * 3 + [["CANCELLED"]] + [["COMPLETED"]] * 20)
    res = run_block(HERE, SAMPLE, {**OPTS, "ignore_errors": True}).raise_for_error()
    out = res.output(0)
    assert out["Result"].tolist() == ["COMPLETED", "CANCELLED", "COMPLETED", "COMPLETED", "COMPLETED"]
    assert out["Failed at stage"].tolist()[1] == 1 and out["Job IDs"].tolist()[1] == "JOB_4"
    assert len(fake.calls("/w/execute")) == 1 + 2 + 1 + 2 * 3  # the failed pass's stage 2 is skipped
    assert res.final_message == "5 passes, 4 completed, 1 failed."


def test_failed_before_stage_stops_before_any_parameter_is_set(serve):
    fake = serve(jobs=["FAILED"])
    res = run_block(HERE, SAMPLE, {**OPTS, "ignore_errors": True})
    assert res.status == "aborted" and "before the loop ended FAILED" in res.final_message
    assert fake.calls("/w/updateparams") == []


def test_cancelled_stage_is_not_restarted_forever(serve):
    # The original started a cancelled stage again, without end
    fake = serve(jobs=["CANCELLED"])
    res = run_block(HERE, SAMPLE, {**OPTS, "Block_Names_Before": ""})
    assert res.status == "aborted" and "ended CANCELLED at stage 1" in res.final_message
    assert len(fake.calls("/w/execute")) == 1


def test_values_become_valid_json(serve):
    # The original crashed on dates and sent NaN for missing numbers
    fake = serve(jobs=["COMPLETED"])
    df = pd.DataFrame({"Week": pd.to_datetime(["2025-03-03", None]), "Target": [1200, None]})
    run_block(HERE, df, {**OPTS, "Parameters": ["Week", "Target"]}).raise_for_error()
    bodies = [r["body"]["updates"] for r in fake.calls("/w/updateparams")]
    assert bodies == [[{"name": "Week", "value": "2025-03-03T00:00:00+00:00"}, {"name": "Target", "value": 1200}],
                      [{"name": "Week", "value": None}, {"name": "Target", "value": None}]]


def test_server_errors_and_busy_project(serve):
    serve(params=(400, {"status": "FAIL", "errorType": "PARAM_NOT_FOUND", "errorMessage": "Parameter 'Region' not found"}))
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted" and "Parameter 'Region' not found" in res.final_message
    busy = (409, {"errorType": "WORKFLOW_ALREADY_RUNNING"})
    fake = serve(execute=[busy] * 30000)
    res = run_block(HERE, SAMPLE, {**OPTS, "busy_wait_minutes": 0})
    assert res.status == "aborted" and "still busy" in res.final_message and len(fake.calls("/w/execute")) == 1
    serve(jobs=["QUEUED"])
    res = run_block(HERE, SAMPLE, {**OPTS, "busy_wait_minutes": 0})
    assert res.status == "aborted" and "Concurrent Workflow Jobs" in res.final_message
    fake = serve(jobs=["COMPLETED"])
    run_block(HERE, SAMPLE, {**OPTS, "username": "scheduler", "password": "example-only"}).raise_for_error()
    assert all(r["headers"].get("authorization", "").startswith("Basic ") for r in fake.requests)


def test_empty_input_runs_only_the_before_stage(serve):
    fake = serve(jobs=["COMPLETED"])
    df = pd.DataFrame({"Region": pd.Series([], dtype=object), "Report title": pd.Series([], dtype=object)})
    res = run_block(HERE, df, OPTS).raise_for_error()
    assert sequence(fake) == ["run Sales database refresh"]
    assert len(res.output(0)) == 0
    assert res.final_message == "No records in the input: nothing was run after the stage before the loop."


def test_option_checks(serve):
    fake = serve()
    for options, words in [({**OPTS, "Iox_File_Url": ""}, "Project address"),
                           ({**OPTS, "Parameters": []}, "Choose the parameter fields"),
                           ({**OPTS, "Parameters": ["Area"]}, "Not in the input: Area")]:
        res = run_block(HERE, SAMPLE, options)
        assert res.status == "aborted" and words in res.final_message
    assert run_block(HERE, None, OPTS).status == "aborted"
    assert fake.requests == []


def test_many_records(serve):
    fake = serve(jobs=["COMPLETED"])
    n = 1000
    df = pd.DataFrame({"Region": [f"R{i}" for i in range(n)], "Report title": ["t"] * n})
    res = run_block(HERE, df, OPTS).raise_for_error()
    assert len(res.output(0)) == n and len(fake.calls("/w/execute")) == 1 + 2 * n
