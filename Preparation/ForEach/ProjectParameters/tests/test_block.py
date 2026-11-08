"""Tests for Project Parameters Batch Setting. No Omniscope server is called: urllib3.PoolManager is replaced by a
fake that answers like a project's Workflow REST API (w/updateparams) and records each request, so the tests check
the exact requests the block would send. What they cannot check: that a real server accepts them as documented."""
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
SAMPLE = os.path.join(HERE, "sample-data", "project-settings.csv")
OPTS = {"Iox_File_Url": "Project", "Parameters": ["Region", "Minimum order", "Currency"]}


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


def test_sample_sets_each_records_parameters_in_its_project(serve):
    fake = serve()
    res = run_block(HERE, SAMPLE, OPTS).raise_for_error()
    calls = fake.calls("/w/updateparams")
    assert [c["url"] for c in calls] == [
        f"http://127.0.0.1:24679/Branch%20reports/{p}.iox/w/updateparams"
        for p in ["Leeds", "York", "Bristol", "Dublin", "Cork"]]
    assert calls[3]["body"] == {"updates": [{"name": "Region", "value": "Ireland"},
                                            {"name": "Minimum order", "value": 200},
                                            {"name": "Currency", "value": "EUR"}]}
    out = res.output(0)
    assert len(out) == 5 and list(out.columns) == ["Project", "Region", "Minimum order", "Currency"]
    assert res.final_message == "Set 3 parameter(s) in 5 record(s), 5 project(s)."


def test_values_become_valid_json(serve):
    # The original crashed on a date (Timestamp is not JSON serialisable) and sent NaN, which is not JSON
    fake = serve()
    df = pd.DataFrame({"Project": ["http://h/A.iox", "http://h/A.iox"], "From": pd.to_datetime(["2025-04-01", None]),
                       "Limit": [10, None], "Live": [True, False]})
    run_block(HERE, df, {"Iox_File_Url": "Project", "Parameters": ["From", "Limit", "Live"]}).raise_for_error()
    raw = "".join(c["raw"] for c in fake.calls("/w/updateparams"))
    assert "NaN" not in raw
    assert [c["body"]["updates"] for c in fake.calls("/w/updateparams")] == [
        [{"name": "From", "value": "2025-04-01T00:00:00+00:00"}, {"name": "Limit", "value": 10},
         {"name": "Live", "value": True}],
        [{"name": "From", "value": None}, {"name": "Limit", "value": None}, {"name": "Live", "value": False}]]


def test_failed_update_names_the_record_and_the_servers_reason(serve):
    # The original's message was "Unexpected server error <urllib3.response.HTTPResponse object at 0x...>"
    serve(params=(400, {"status": "FAIL", "errorType": "PARAM_NOT_FOUND", "errorMessage": "Parameter 'Currency' not found"}))
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted"
    assert res.final_message.startswith("Record 1: setting parameters of http://127.0.0.1:24679/Branch%20reports/"
                                        "Leeds.iox/ failed (HTTP 400: Parameter 'Currency' not found)")
    serve(params=(403, None))
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted" and "Project parameters access via APIs" in res.final_message


def test_bad_or_missing_address_stops_before_anything_is_changed(serve):
    # The original crashed on a missing address (float has no endswith) after updating the earlier projects
    fake = serve()
    df = pd.read_csv(SAMPLE)
    df.loc[3, "Project"] = None
    res = run_block(HERE, df, OPTS)
    assert res.status == "aborted" and res.final_message.startswith("Record 4: the project address must end in .iox")
    df.loc[3, "Project"] = "http://127.0.0.1:24679/Branch reports/"
    res = run_block(HERE, df, OPTS)
    assert res.status == "aborted" and "Record 4" in res.final_message
    assert fake.requests == []


def test_pasted_report_address_and_credentials(serve):
    fake = serve()
    df = pd.DataFrame({"Project": ["https://omniscope.example.com/Sales/Pack.iox/r/Report/#Tab"], "Region": ["North"]})
    run_block(HERE, df, {"Iox_File_Url": "Project", "Parameters": ["Region"], "username": "batch",
                         "password": "example-only"}).raise_for_error()
    call = fake.requests[0]
    assert call["url"] == "https://omniscope.example.com/Sales/Pack.iox/w/updateparams"
    assert call["headers"]["authorization"] == urllib3.make_headers(basic_auth="batch:example-only")["authorization"]


def test_address_field_is_not_sent_as_a_parameter(serve):
    fake = serve()
    run_block(HERE, SAMPLE, {**OPTS, "Parameters": ["Project", "Region"]}).raise_for_error()
    assert fake.requests[0]["body"] == {"updates": [{"name": "Region", "value": "North"}]}


def test_empty_input_passes_through(serve):
    fake = serve()
    df = pd.DataFrame({"Project": pd.Series([], dtype=object), "Region": pd.Series([], dtype=object)})
    res = run_block(HERE, df, {"Iox_File_Url": "Project", "Parameters": ["Region"]}).raise_for_error()
    assert fake.requests == [] and len(res.output(0)) == 0 and list(res.output(0).columns) == ["Project", "Region"]
    assert res.final_message == "No records in the input: nothing was set."


def test_option_checks(serve):
    fake = serve()
    for options, words in [({**OPTS, "Iox_File_Url": None}, "field holding the project addresses"),
                           ({**OPTS, "Parameters": None}, "Choose the parameter fields"),
                           ({**OPTS, "Parameters": ["Area"]}, "Not in the input: Area"),
                           ({**OPTS, "Parameters": ["Project"]}, "other than the project address field")]:
        res = run_block(HERE, SAMPLE, options)
        assert res.status == "aborted" and words in res.final_message, res.final_message
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and "Connect the records" in res.final_message
    assert fake.requests == []


def test_many_records(serve):
    fake = serve()
    n = 5000
    df = pd.DataFrame({"Project": [f"http://127.0.0.1:24679/P/{i % 50}.iox/" for i in range(n)],
                       "Limit": np.arange(n)})
    res = run_block(HERE, df, {"Iox_File_Url": "Project", "Parameters": ["Limit"]}).raise_for_error()
    assert len(fake.calls("/w/updateparams")) == n and len(res.output(0)) == n
    assert res.final_message == f"Set 1 parameter(s) in {n} record(s), 50 project(s)."
