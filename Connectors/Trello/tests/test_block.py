"""Tests for the Trello block against canned Trello responses (tests/canned/, written by tests/make_canned.py).
No test calls Trello: requests.Session.request is replaced by a fake that answers from the canned files."""

import json
import os
import time
from urllib.parse import parse_qsl, urlsplit

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
AUTH = {"apiKey": "k3y", "apiToken": "t0ken"}
BOARD = "64b0c0ffee0000000000b001"
WRITING = "64c0c0ffee00000000000l02"
CARD = "64d0c0ffee000000000c0000"
CHECKLIST = "64f0c0ffee000000000cl001"


def canned(name):
    with open(os.path.join(CANNED, name), encoding="utf-8") as fh:
        return json.load(fh)


def response(status, body):
    r = requests.Response()
    r.status_code = status
    r._content = (body if isinstance(body, str) else json.dumps(body)).encode("utf-8")
    r.url = "https://api.trello.com/"
    return r


ROUTES = {
    "/1/organizations/ws-content/boards": "boards.json",
    f"/1/boards/{BOARD}/lists": "lists.json",
    f"/1/boards/{BOARD}/cards": "cards-board.json",
    f"/1/lists/{WRITING}/cards": "cards-list.json",
    f"/1/cards/{CARD}/checklists": "checklists.json",
    f"/1/checklists/{CHECKLIST}/checkItems": "checkitems.json",
    f"/1/checklists/{CHECKLIST}/checkitems": "checkitems.json",
}


class FakeTrello:
    def __init__(self, status=200, routes=None):
        self.calls = []
        self.status = status
        self.routes = routes or {}

    def __call__(self, session, method, url, params=None, headers=None, **kw):
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        query.update({k: str(v) for k, v in (params or {}).items()})
        self.calls.append(
            {
                "method": method,
                "url": url,
                "path": parts.path,
                "params": query,
                "headers": dict(session.headers, **(headers or {})),
            }
        )
        if self.status != 200:
            return response(self.status, "invalid key")
        if parts.path in self.routes:
            return response(200, self.routes[parts.path])
        if parts.path in ROUTES:
            return response(200, canned(ROUTES[parts.path]))
        if parts.path == "/1/search":
            return response(200, canned("search.json"))
        return response(404, "The requested resource was not found.")


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def trello(monkeypatch):
    return install(monkeypatch, FakeTrello())


def test_board_lists_and_all_its_cards(trello):
    res = run_block(HERE, None, {**AUTH, "boardID": BOARD}).raise_for_error()
    lists, cards = res.output(1), res.output(2)
    assert lists["name"].tolist() == ["To plan", "Writing", "Design", "Scheduled", "Published"]
    assert len(cards) == 16
    assert cards.columns.tolist()[:6] == ["id", "name", "desc", "closed", "idList", "listName"]
    assert cards["listName"].value_counts().to_dict() == {
        "To plan": 5,
        "Writing": 4,
        "Published": 3,
        "Scheduled": 2,
        "Design": 2,
    }
    story = cards[cards["name"] == "Customer story: Fernhill Garden Centre"].iloc[0]
    assert story["labels"] == "Blog, Social"
    assert story["due"] == pd.Timestamp("2025-03-11T09:00:00Z")
    assert str(cards["dateLastActivity"].dt.tz) == "UTC"
    # a label with no name is shown by its colour; members joined
    assert cards.loc[cards["name"] == "Price list refresh announcement", "labels"].item() == "Blog, red"
    assert cards["idMembers"].iloc[0] == "m1"
    assert cards["checkItems"].iloc[0] == 4 and cards["checkItemsChecked"].iloc[0] == 4
    for df in (lists, cards):
        for c in df.columns:
            assert not df[c].map(lambda v: isinstance(v, (list, dict))).any(), c
    assert res.final_message == "Loaded 5 lists, 16 cards."


def test_every_output(trello):
    res = run_block(
        HERE,
        None,
        {
            **AUTH,
            "workspaceID": "ws-content",
            "boardID": BOARD,
            "listID": WRITING,
            "cardID": CARD,
            "checklistID": CHECKLIST,
            "searchString": "newsletter",
        },
    )
    res.raise_for_error()
    assert res.output(0)["name"].tolist() == ["Content calendar", "Trade show 2025", "Website fixes (archived)"]
    assert res.output(0)["closed"].tolist() == [False, False, True]
    cards = res.output(2)
    assert len(cards) == 4 and set(cards["listName"]) == {"Writing"}  # the list's cards, with the list's name
    checklists = res.output(3)
    assert checklists[["name", "checkItems", "checkItemsComplete"]].values.tolist() == [["Before sending", 4, 2]]
    items = res.output(4)
    assert items["state"].tolist() == ["complete", "complete", "incomplete", "incomplete"]
    found = res.output(5)
    assert found["name"].tolist() == ["March newsletter", "April newsletter", "May newsletter"]


def test_key_and_token_are_sent_in_a_header_not_the_address(trello):
    # The original put them in the address, so an error message (which quotes the address) showed them
    run_block(HERE, None, {**AUTH, "boardID": BOARD}).raise_for_error()
    for call in trello.calls:
        assert "t0ken" not in call["url"] and "token" not in call["params"]
        assert call["headers"]["Authorization"] == 'OAuth oauth_consumer_key="k3y", oauth_token="t0ken"'


def test_search_text_is_encoded_and_asks_for_up_to_1000_cards(trello):
    run_block(HERE, None, {**AUTH, "searchString": "price & stock #2"}).raise_for_error()
    call = trello.calls[0]
    assert call["path"] == "/1/search"
    assert call["params"]["query"] == "price & stock #2"  # the original cut the query at "&"
    assert call["params"]["modelTypes"] == "cards" and call["params"]["cards_limit"] == "1000"


def test_fields_are_asked_for(trello):
    run_block(HERE, None, {**AUTH, "workspaceID": "ws-content"}).raise_for_error()
    assert trello.calls[0]["params"]["fields"].startswith("id,name,desc,closed")


def test_blank_options_are_ignored(trello):
    # The original treated "" as set and called /boards//lists
    res = run_block(HERE, None, {**AUTH, "boardID": BOARD, "workspaceID": "", "listID": "  "}).raise_for_error()
    assert [c["path"] for c in trello.calls] == [f"/1/boards/{BOARD}/lists", f"/1/boards/{BOARD}/cards"]
    assert res.output(0) is None


def test_empty_board_gives_outputs_with_fields(monkeypatch):
    fake = install(monkeypatch, FakeTrello(routes={f"/1/boards/{BOARD}/lists": [], f"/1/boards/{BOARD}/cards": []}))
    res = run_block(HERE, None, {**AUTH, "boardID": BOARD}).raise_for_error()
    assert len(res.output(1)) == 0 and res.output(1).columns.tolist() == ["id", "name", "closed", "pos", "idBoard"]
    assert len(res.output(2)) == 0 and "listName" in res.output(2).columns
    assert len(fake.calls) == 2


def test_wrong_key_wrong_id_and_nothing_chosen(monkeypatch):
    install(monkeypatch, FakeTrello(status=401))
    res = run_block(HERE, None, {**AUTH, "boardID": BOARD})
    assert res.status == "aborted" and "API key and token" in res.final_message
    install(monkeypatch, FakeTrello())
    res = run_block(HERE, None, {**AUTH, "cardID": "no-such-card"})
    assert res.status == "aborted" and "check the id" in res.final_message
    res = run_block(HERE, None, AUTH)
    assert res.status == "aborted" and "at least one" in res.final_message
    res = run_block(HERE, None, {"boardID": BOARD})
    assert res.status == "aborted" and "API key" in res.final_message


def test_large_board(monkeypatch):
    base = canned("cards-board.json")
    big = [dict(base[i % 16], id=f"c{i}") for i in range(20_000)]
    install(monkeypatch, FakeTrello(routes={f"/1/boards/{BOARD}/cards": big}))
    t0 = time.time()
    cards = run_block(HERE, None, {**AUTH, "boardID": BOARD}).raise_for_error().output(2)
    assert len(cards) == 20_000 and cards["listName"].notna().all()
    assert time.time() - t0 < 60


def test_placeholder_matches_the_canned_output(trello):
    cards = run_block(HERE, None, {**AUTH, "boardID": BOARD}).raise_for_error().output(2)
    placeholder = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"), dtype=str, keep_default_na=False)
    assert placeholder.columns.tolist() == cards.columns.tolist()
    assert placeholder["id"].tolist() == cards["id"].tolist()
