"""Tests for the Overpass Street Coordinates block against an invented Overpass server (tests/canned/ways.json,
written by tests/make_canned.py). No test calls Overpass: requests.Session.request is replaced by a fake that
reads the block's Overpass QL query and answers from the canned ways."""
import json
import os
import re
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = pd.read_csv(os.path.join(HERE, "sample-data", "deliveries.csv"))
with open(os.path.join(HERE, "tests", "canned", "ways.json"), encoding="utf-8") as fh:
    WAYS = json.load(fh)["elements"]
DEFAULT = "https://overpass-api.de/api/interpreter"
LEEDS = "53.77, -1.58, 53.83, -1.50"
QL_STRING = r'"((?:[^"\\]|\\.)*)"'


def unquote(s):
    return re.sub(r"\\(.)", r"\1", s)


def response(status, body):
    r = requests.Response()
    r.status_code = status
    r._content = (json.dumps(body) if not isinstance(body, str) else body).encode("utf-8")
    r.headers["Content-Type"] = "application/json"
    return r


class FakeOverpass:
    """Answers `way["highway"]["name"=...](bbox);out geom;` queries from the canned ways, like the Overpass API."""

    def __init__(self, script=None, ways=None):
        self.calls = []
        self.script = list(script or [])
        self.ways = WAYS if ways is None else ways

    def __call__(self, session, method, url, data=None, **kw):
        query = (data or {}).get("data", "")
        self.calls.append({"method": method, "url": url, "query": query,
                           "user_agent": session.headers.get("User-Agent", "")})
        if self.script:
            return self.script.pop(0)
        m = re.fullmatch(r'\[out:json\]\[timeout:\d+\];way\["highway"\]\["name"(=|~)' + QL_STRING +
                         r'(,i)?\](\((-?[\d.]+),(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)\))?;out geom;', query)
        if not m:
            return response(400, "<html>Error: line 1: parse error</html>")
        op, value, icase, box = m.group(1), unquote(m.group(2)), m.group(3), m.group(4)
        out = []
        for w in self.ways:
            tags = w.get("tags", {})
            name = tags.get("name")
            if "highway" not in tags or name is None:
                continue
            if op == "=" and name != value:
                continue
            if op == "~" and not re.search(value, name, re.I if icase else 0):
                continue
            if box:
                s, west, n, e = (float(m.group(i)) for i in range(5, 9))
                if not any(s <= g["lat"] <= n and west <= g["lon"] <= e for g in w["geometry"]):
                    continue
            out.append(w)
        return response(200, {"version": 0.6, "elements": out})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))
    return sleeps


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def overpass(monkeypatch):
    return install(monkeypatch, FakeOverpass())


def run(df=SAMPLE, **options):
    return run_block(HERE, [df], {"addressField": "Street", "bbox": LEEDS, **options})


def test_points_of_the_sample_streets(overpass):
    res = run().raise_for_error()
    out = res.output(0)
    assert out.columns.tolist() == ["Street", "Street name", "Way ID", "Point", "Node ID", "Latitude", "Longitude"]
    assert len(out) == 9 + 7 + 4 + 6 + 5
    assert out.groupby("Street")["Way ID"].nunique().to_dict() == {
        "High Street": 2, "Station Road": 1, "Church Lane": 1, "Mill Street": 2, "Park Avenue": 1}
    assert (out["Street"] == out["Street name"]).all()
    first_way = out[out["Way ID"] == out["Way ID"].iloc[0]]
    assert first_way["Point"].tolist() == list(range(1, len(first_way) + 1))
    assert str(out["Latitude"].dtype) == "float64" and str(out["Way ID"].dtype) == "Int64"
    assert out["Latitude"].between(53.77, 53.83).all() and out["Longitude"].between(-1.58, -1.50).all()
    assert res.final_message == ("31 points on 7 ways for 5 of 6 street name(s). "
                                 "No street found for 1, such as 'Kingfisher Way'.")


def test_each_name_is_asked_once_with_a_user_agent(overpass):
    run().raise_for_error()
    assert len(overpass.calls) == 6  # High Street twice in the input, one empty value
    call = overpass.calls[0]
    assert call["method"] == "POST" and call["url"] == DEFAULT
    # the public servers refuse library-default User-Agents since April 2026
    assert call["user_agent"].startswith("Omniscope-Overpass-Street-Coordinates/")
    assert call["query"] == ('[out:json][timeout:120];way["highway"]["name"="High Street"]'
                             '(53.77,-1.58,53.83,-1.5);out geom;')


def test_only_streets_are_returned(overpass):
    # The original matched any way whose name contained the value, buildings included
    out = run(pd.DataFrame({"Street": ["High Street Surgery"]}), matchMode="contains").raise_for_error().output(0)
    assert len(out) == 0


def test_contains_finds_longer_names_in_any_case(overpass):
    out = run(pd.DataFrame({"Street": ["high street"]}), matchMode="contains").raise_for_error().output(0)
    assert sorted(out["Street name"].unique()) == ["High Street", "High Street North"]
    assert (out["Street"] == "high street").all() and len(out) == 12
    assert '["name"~"high street",i]' in overpass.calls[0]["query"]


def test_exact_is_the_default_and_case_sensitive(overpass):
    assert len(run(pd.DataFrame({"Street": ["high street"]})).raise_for_error().output(0)) == 0


def test_names_with_quotes_and_regex_characters_are_quoted(monkeypatch):
    # The original pasted the name into the query: a quote broke the query, and ( or . changed the match
    name = 'O"Brien\'s Way (Old) St.'
    ways = [dict(WAYS[0], tags={"highway": "residential", "name": name}),
            dict(WAYS[1], tags={"highway": "residential", "name": "O\"Brien's Way XOldX StX"})]
    install(monkeypatch, FakeOverpass(ways=ways))
    for mode in ("exact", "contains"):
        out = run(pd.DataFrame({"Street": [name]}), matchMode=mode).raise_for_error().output(0)
        assert out["Street name"].unique().tolist() == [name], mode


def test_bounding_box(overpass):
    out = run(bbox="51.4, -0.2, 51.6, 0.0").raise_for_error().output(0)
    assert len(out) == 0
    out = run(bbox="").raise_for_error().output(0)  # whole world
    assert len(out) == 31 and overpass.calls[-1]["query"].endswith('"];out geom;')
    for bad in ("53.8,-1.5", "north, west, south, east", "53.83, -1.58, 53.77, -1.50", "95,0,96,1"):
        res = run(bbox=bad)
        assert res.status == "aborted" and "Bounding box" in res.final_message, bad


def test_busy_server_is_retried_then_gives_up(monkeypatch, no_sleep):
    fake = install(monkeypatch, FakeOverpass(script=[response(429, "rate limited"), response(504, "busy")]))
    assert len(run(pd.DataFrame({"Street": ["Park Avenue"]})).raise_for_error().output(0)) == 5
    assert len(fake.calls) == 3 and no_sleep == [30, 30]
    install(monkeypatch, FakeOverpass(script=[response(429, "rate limited")] * 4))
    res = run(pd.DataFrame({"Street": ["Park Avenue"]}))
    assert res.status == "aborted" and "429" in res.final_message


def test_refused_and_timed_out_queries_abort(monkeypatch):
    install(monkeypatch, FakeOverpass(script=[response(406, "Not Acceptable")]))
    res = run()
    assert res.status == "aborted" and "HTTP 406" in res.final_message
    remark = {"elements": [], "remark": "runtime error: Query timed out in \"query\" at line 1 after 120 seconds."}
    install(monkeypatch, FakeOverpass(script=[response(200, remark)]))
    res = run()
    assert res.status == "aborted" and "timed out" in res.final_message


def test_custom_endpoint(overpass):
    run(endpoint="https://overpass.example.org/api/interpreter").raise_for_error()
    assert overpass.calls[0]["url"] == "https://overpass.example.org/api/interpreter"
    assert run(endpoint="overpass.example.org").status == "aborted"


def test_input_field_with_an_output_name(overpass):
    out = run(pd.DataFrame({"Latitude": ["Church Lane"]}), addressField="Latitude").raise_for_error().output(0)
    assert out.columns[0] == "Latitude (input)" and len(out) == 4


def test_empty_input_and_missing_values(overpass):
    out = run(SAMPLE.iloc[0:0]).raise_for_error().output(0)
    assert len(out) == 0 and out.columns.tolist()[1:] == ["Street name", "Way ID", "Point", "Node ID", "Latitude",
                                                          "Longitude"]
    out = run(pd.DataFrame({"Street": [None, "", "  "]}, dtype=object)).raise_for_error().output(0)
    assert len(out) == 0 and overpass.calls == []


def test_wrong_types_and_missing_choices(overpass):
    res = run(pd.DataFrame({"Street": [12, 14]})).raise_for_error()  # numbers are looked up as names
    assert len(res.output(0)) == 0 and "No street found for 2" in res.final_message
    assert run_block(HERE, None, {"addressField": "Street"}).status == "aborted"
    res = run_block(HERE, [SAMPLE], {})
    assert res.status == "aborted" and "Street name field" in res.final_message


def test_many_street_names(overpass):
    df = pd.DataFrame({"Street": [f"Street {i}" for i in range(2000)] + ["Station Road"] * 3000})
    started = time.perf_counter()
    res = run(df).raise_for_error()
    assert len(overpass.calls) == 2001 and len(res.output(0)) == 7
    assert time.perf_counter() - started < 30
