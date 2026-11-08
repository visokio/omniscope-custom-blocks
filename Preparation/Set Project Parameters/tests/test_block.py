"""Tests for Set Project Parameters. No Omniscope server is called: urllib3.PoolManager is replaced by a fake that
answers like a project's Workflow REST API (w/updateparams) and records each request, so the tests check the exact
request the block would send. What they cannot check: that a real server accepts it and that the parameters change
as documented."""
import json
import os
import time
from types import SimpleNamespace

import pandas as pd
import pytest
import urllib3

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "parameter-values.csv")
URL = "http://127.0.0.1:24679/Community/Demo/demo.iox/"
OPTS = {"Iox_File_Url": URL, "Params_Name": "Parameter", "Params_Value": "Value"}


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


def test_sample_sets_all_parameters_in_one_request(serve):
    fake = serve()
    res = run_block(HERE, SAMPLE, OPTS).raise_for_error()
    assert len(fake.requests) == 1
    call = fake.requests[0]
    assert call["method"] == "POST" and call["url"] == URL + "w/updateparams"
    assert call["body"] == {"updates": [{"name": "Region", "value": "South West"},
                                        {"name": "Report heading", "value": "South West branches: March 2025"},
                                        {"name": "Currency", "value": "GBP"}],
                            "waitForIdle": False}
    assert call["headers"]["Content-Type"] == "application/json"
    out = res.output(0)
    assert len(out) == 3 and list(out.columns) == ["Parameter", "Value"]
    assert res.final_message == ("Set 3 parameter(s): Region = South West, Report heading = South West branches: "
                                 "March 2025, Currency = GBP.")


def test_refused_update_is_reported_not_announced_as_done(serve):
    # The original never looked at the answer and always said "Project parameters update enqueued."
    serve(params=(400, {"status": "FAIL", "errorType": "PARAM_NOT_FOUND", "errorMessage": "Parameter 'Currency' not found"}))
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted" and "Parameter 'Currency' not found" in res.final_message
    serve(params=(401, None))
    res = run_block(HERE, SAMPLE, OPTS)
    assert res.status == "aborted" and "Project parameters access via APIs" in res.final_message
    serve(params=(404, None))
    res = run_block(HERE, SAMPLE, {**OPTS, "Iox_File_Url": "http://127.0.0.1:24679/Nowhere/x.iox"})
    assert res.status == "aborted" and "Is there a project at http://127.0.0.1:24679/Nowhere/x.iox/?" in res.final_message


def test_numbers_dates_and_missing_values_become_valid_json(serve):
    # The original sent NaN (not JSON) for a missing value and crashed on a date
    fake = serve()
    df = pd.DataFrame({"Parameter": ["Limit", "Rate", "Empty"], "Value": [5, None, 7]})
    run_block(HERE, df, OPTS).raise_for_error()
    assert "NaN" not in fake.requests[0]["raw"]
    assert fake.requests[0]["body"]["updates"] == [{"name": "Limit", "value": 5}, {"name": "Rate", "value": None},
                                                   {"name": "Empty", "value": 7}]
    fake = serve()
    df = pd.DataFrame({"Parameter": ["From"], "Value": pd.to_datetime(["2025-03-01"])})
    run_block(HERE, df, OPTS).raise_for_error()
    assert fake.requests[0]["body"]["updates"] == [{"name": "From", "value": "2025-03-01T00:00:00+00:00"}]


def test_a_name_given_twice_sets_the_later_value(serve):
    fake = serve()
    df = pd.DataFrame({"Parameter": ["Region", "Currency", "Region"], "Value": ["North", "GBP", "South"]})
    res = run_block(HERE, df, OPTS).raise_for_error()
    assert fake.requests[0]["body"]["updates"] == [{"name": "Currency", "value": "GBP"},
                                                   {"name": "Region", "value": "South"}]
    assert res.output(0)["Value"].tolist() == ["GBP", "South"]


def test_missing_name_stops_before_sending(serve):
    fake = serve()
    df = pd.DataFrame({"Parameter": ["Region", None], "Value": ["North", "x"]})
    res = run_block(HERE, df, OPTS)
    assert res.status == "aborted" and res.final_message == "Record 2 has no parameter name."
    assert fake.requests == []


def test_address_checks_and_credentials(serve):
    fake = serve()
    for bad in ["", None, "127.0.0.1:24679/Folder/Project.iox", "http://127.0.0.1:24679/Folder/"]:
        res = run_block(HERE, SAMPLE, {**OPTS, "Iox_File_Url": bad})
        assert res.status == "aborted" and res.final_message.startswith("Project address:"), bad
    assert fake.requests == []
    run_block(HERE, SAMPLE, {**OPTS, "Iox_File_Url": URL + "r/Report/", "username": "u", "password": "example-only"}
              ).raise_for_error()
    assert fake.requests[0]["url"] == URL + "w/updateparams"
    assert fake.requests[0]["headers"]["authorization"] == urllib3.make_headers(basic_auth="u:example-only")["authorization"]


def test_empty_input_sends_nothing(serve):
    # The original sent an empty update list
    fake = serve()
    df = pd.DataFrame({"Parameter": pd.Series([], dtype=object), "Value": pd.Series([], dtype=object)})
    res = run_block(HERE, df, OPTS).raise_for_error()
    assert fake.requests == [] and len(res.output(0)) == 0
    assert res.final_message == "No records in the input: nothing was set."


def test_option_and_input_checks(serve):
    fake = serve()
    res = run_block(HERE, SAMPLE, {**OPTS, "Params_Value": None})
    assert res.status == "aborted" and "Choose the field" in res.final_message
    res = run_block(HERE, SAMPLE, {**OPTS, "Params_Value": "New value"})
    assert res.status == "aborted" and res.final_message == "Not in the input: New value"
    res = run_block(HERE, None, OPTS)
    assert res.status == "aborted" and "Connect the records" in res.final_message
    assert fake.requests == []


def test_many_parameters_in_one_request(serve):
    fake = serve()
    n = 10000
    df = pd.DataFrame({"Parameter": [f"P{i}" for i in range(n)], "Value": [f"v{i}" for i in range(n)]})
    res = run_block(HERE, df, OPTS).raise_for_error()
    assert len(fake.requests) == 1 and len(fake.requests[0]["body"]["updates"]) == n and len(res.output(0)) == n


def test_placeholder_is_the_block_output_for_the_sample(serve):
    # The demo shows sample-data/placeholder.csv in place of the block's Set output: it must stay identical.
    serve()
    out = run_block(HERE, SAMPLE, OPTS).raise_for_error().output(0)
    expected = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"))
    pd.testing.assert_frame_equal(out.reset_index(drop=True), expected, check_dtype=False)
