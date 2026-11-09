"""Tests for the Slim CD Transaction block against an invented SearchTransactions2 reply
(tests/canned/search-reply.json, written by tests/make_canned.py). No test calls Slim CD:
requests.Session.request is replaced by a fake that records each request and answers from the canned reply."""
import copy
import json
import os

import pandas as pd
import pytest
import requests

from harness.runner import run_block
from omniscope.api import _broad_type as broad  # the Omniscope field type a pandas dtype becomes

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
URL = "https://stats.slimcd.com/soft/json/jsonscript.asp"
with open(os.path.join(HERE, "tests", "canned", "search-reply.json"), encoding="utf-8") as fh:
    REPLY = json.load(fh)
AUTH = {"username": "shopadmin", "password": "s3cret-Pass", "siteid": "100200300"}


def response(status, body):
    r = requests.Response()
    r.status_code = status
    r._content = (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
    r.url = URL + "?service=SearchTransactions2&username=shopadmin&password=s3cret-Pass&siteid=100200300"
    return r


class FakeSlimCD:
    def __init__(self, answer=None, status=200, exc=None):
        self.calls = []
        self.answer = REPLY if answer is None else answer
        self.status = status
        self.exc = exc

    def __call__(self, session, method, url, params=None, **kw):
        self.calls.append({"method": method.upper(), "url": url, "params": dict(params or {})})
        if self.exc:
            raise self.exc
        return response(self.status, self.answer)


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def slim(monkeypatch):
    return install(monkeypatch, FakeSlimCD())


def reply_with(transactions=None, **reply_fields):
    r = copy.deepcopy(REPLY)
    if transactions is not None:
        r["reply"]["datablock"] = {"Transactions": {"Transaction": transactions}}
    r["reply"].update(reply_fields)
    return r


def test_transactions_of_the_sample(slim):
    res = run_block(HERE, None, AUTH).raise_for_error()
    out = res.output(0)
    assert len(out) == 36 and out.columns[:4].tolist() == ["gateid", "transactiondate", "transtype", "processor"]
    assert str(out["transactiondate"].dtype).startswith("datetime64")
    assert out["transactiondate"].iloc[0] == pd.Timestamp("2026-10-01 17:24:00")
    assert str(out["amount"].dtype) == "float64" and out["amount"].iloc[0] == 231.18
    assert str(out["gateid"].dtype) == "Int64" and out["gateid"].iloc[0] == 1840221000
    assert str(out["cardpresent"].dtype) == "boolean" and out["cardpresent"].sum() == 27
    assert out["transtype"].value_counts().to_dict() == {"SALE": 32, "RETURN": 4}
    assert res.final_message == "36 transaction(s)."


def test_request_sends_only_what_is_set(slim):
    run_block(HERE, None, {**AUTH, "startdate": "2026-10-01", "enddate": " 2026-10-31 ", "lastname": "Hart",
                           "amount": "", "maxrecords": "500"}).raise_for_error()
    (call,) = slim.calls
    assert call["method"] == "GET" and call["url"] == URL
    assert call["params"] == {"service": "SearchTransactions2", "username": "shopadmin", "password": "s3cret-Pass",
                              "siteid": "100200300", "maxrecords": "500", "startdate": "2026-10-01",
                              "enddate": "2026-10-31", "lastname": "Hart"}


def test_zip_codes_keep_leading_zeros(slim):
    # The original converted zip to a whole number: 02134 became 2134 and 02139-4307 became empty
    out = run_block(HERE, None, AUTH).raise_for_error().output(0)
    assert set(out["zip"]) == {"02134", "02139-4307", "02903", "06103", "01608", "03060"}


def test_all_text_keeps_missing_values_missing(monkeypatch):
    tx = copy.deepcopy(REPLY["reply"]["datablock"]["Transactions"]["Transaction"][:2])
    del tx[1]["email"]  # a field one transaction lacks
    install(monkeypatch, FakeSlimCD(reply_with(tx)))
    out = run_block(HERE, None, {**AUTH, "treat_all_output_as_text": True}).raise_for_error().output(0)
    # The original wrote the text "None" / "nan" for missing values
    assert pd.isna(out["email"].iloc[1]) and out["email"].iloc[0] == "grace.okoro@example.com"
    assert not out.isin(["None", "nan", "NaT"]).any().any()
    assert out["amount"].iloc[0] == "231.18" and out["zip"].iloc[0] == "02903"


def test_no_transactions_gives_the_same_field_types(monkeypatch):
    install(monkeypatch, FakeSlimCD())
    full = run_block(HERE, None, AUTH).raise_for_error().output(0)
    install(monkeypatch, FakeSlimCD(reply_with([])))
    empty = run_block(HERE, None, AUTH).raise_for_error().output(0)
    assert len(empty) == 0 and empty.columns.tolist() == full.columns.tolist()
    # The original wrote every field as text when there were no transactions, so the schema changed
    for c in ("transactiondate", "amount", "gateid", "cardpresent"):
        assert broad(empty[c].dtype) == broad(full[c].dtype), c


def test_single_transaction_as_an_object(monkeypatch):
    one = reply_with()
    one["reply"]["datablock"]["Transactions"]["Transaction"] = REPLY["reply"]["datablock"]["Transactions"][
        "Transaction"][0]
    install(monkeypatch, FakeSlimCD(one))
    assert len(run_block(HERE, None, AUTH).raise_for_error().output(0)) == 1


def test_refused_login_aborts(monkeypatch):
    install(monkeypatch, FakeSlimCD(reply_with(responsecode="1", response="Error",
                                               description="Invalid Username/Password")))
    res = run_block(HERE, None, AUTH)
    assert res.status == "aborted"
    assert res.final_message == "Slim CD refused the request (response code 1): Invalid Username/Password"


def test_record_count_only(monkeypatch):
    fake = install(monkeypatch, FakeSlimCD({"reply": {"response": "Success", "responsecode": "0",
                                                      "datablock": {"RecordCount": "36"}}}))
    out = run_block(HERE, None, {**AUTH, "recordcountonly": True}).raise_for_error().output(0)
    assert out.to_dict("records")[0]["recordcount"] == 36 and len(out) == 1
    assert fake.calls[0]["params"]["recordcountonly"] == ""
    # The original reported an empty count as a success when Slim CD refused the login
    install(monkeypatch, FakeSlimCD(reply_with(responsecode="1", description="Invalid Username/Password")))
    res = run_block(HERE, None, {**AUTH, "recordcountonly": True})
    assert res.status == "aborted" and "Invalid Username/Password" in res.final_message


@pytest.mark.parametrize("fake", [FakeSlimCD(status=500, answer="<html>Server error</html>"),
                                  FakeSlimCD(exc=requests.ConnectionError(
                                      "HTTPSConnectionPool(host='stats.slimcd.com'): Max retries exceeded with url: "
                                      "/soft/json/jsonscript.asp?username=shopadmin&password=s3cret-Pass"))])
def test_errors_never_show_the_password(monkeypatch, fake):
    # The original aborted with str(exception), which for requests includes the URL and so the password
    install(monkeypatch, fake)
    res = run_block(HERE, None, AUTH)
    assert res.status == "aborted" and "s3cret-Pass" not in res.final_message


def test_an_answer_that_is_not_json_aborts(monkeypatch):
    # The original treated an HTML page as "no transactions" and finished without error
    install(monkeypatch, FakeSlimCD(answer="<html><body>Maintenance</body></html>"))
    res = run_block(HERE, None, AUTH)
    assert res.status == "aborted" and "not the expected JSON" in res.final_message


def test_options_are_checked(slim):
    for opts, text in [({"username": ""}, "Enter the Slim CD username"), ({"password": None}, "password"),
                       ({"siteid": " "}, "Enter the Site ID"), ({"maxrecords": "lots"}, "Max records")]:
        res = run_block(HERE, None, {**AUTH, **opts})
        assert res.status == "aborted" and text in res.final_message, opts
    assert slim.calls == []
    run_block(HERE, None, {**AUTH, "password": ""}).raise_for_error()  # empty password allowed


def test_many_transactions(monkeypatch):
    base = REPLY["reply"]["datablock"]["Transactions"]["Transaction"]
    many = [dict(base[i % 36], gateid=str(1900000000 + i)) for i in range(20000)]
    install(monkeypatch, FakeSlimCD(reply_with(many)))
    out = run_block(HERE, None, AUTH).raise_for_error().output(0)
    assert len(out) == 20000 and out["gateid"].is_unique and out["amount"].notna().all()
