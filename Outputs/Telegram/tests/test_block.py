"""Tests for Send to Telegram. Nothing is sent to Telegram: requests.post is replaced by a stand-in that records each
request and answers like the Bot API (the canned replies in tests/canned/), including its refusals of an empty
message, a message over 4,096 characters, an unknown chat and a bad token."""
import html
import json
import os
import re
import time

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "low-stock.csv")
CANNED = os.path.join(HERE, "tests", "canned")
TOKEN = "7000000001:AAtest-token"
SETTINGS = {"bot_token": TOKEN, "chat_id": "-1001234567890"}


def canned(name, status=200):
    r = requests.Response()
    r.status_code = status
    with open(os.path.join(CANNED, name + ".json"), encoding="utf-8") as fh:
        r._content = fh.read().encode("utf-8")
    r.headers["Content-Type"] = "application/json"
    return r


class FakeTelegram:
    def __init__(self, chats=("-1001234567890", "@stock_alerts"), network_error=False):
        self.calls, self.chats, self.network_error = [], chats, network_error

    def __call__(self, url, json=None, timeout=None, **kw):
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        if self.network_error:
            raise requests.ConnectionError(f"HTTPSConnectionPool(host='api.telegram.org'): Max retries exceeded "
                                           f"with url: /bot{TOKEN}/sendMessage")
        if url != f"https://api.telegram.org/bot{TOKEN}/sendMessage":
            return canned("error.not_found", 404)
        if json["chat_id"] not in self.chats:
            return canned("error.chat_not_found", 400)
        shown = json["text"]
        if json.get("parse_mode") == "HTML":
            shown = html.unescape(re.sub(r"</?pre>", "", shown))
        if not shown.strip():
            return canned("error.message_text_is_empty", 400)
        if len(shown.encode("utf-16-le")) // 2 > 4096:  # Telegram counts UTF-16 code units
            return canned("error.message_too_long", 400)
        return canned("sendMessage")

    def texts(self):
        return [c["json"]["text"] for c in self.calls]


@pytest.fixture
def telegram(monkeypatch):
    fake = FakeTelegram()
    monkeypatch.setattr(requests, "post", fake)
    return fake


def test_sample_as_text_one_line_per_record(telegram):
    res = run_block(HERE, SAMPLE, SETTINGS).raise_for_error()
    assert len(telegram.calls) == 1 and telegram.calls[0]["timeout"]
    lines = telegram.texts()[0].split("\n")
    assert lines[0] == "Terracotta pot 30cm Leeds 14 40 2025-03-03"
    assert lines[3] == "Netting 4m Bristol 0 15"  # the original wrote 'NaT' for the missing date
    assert len(lines) == 8 and "parse_mode" not in telegram.calls[0]["json"]
    out = res.output(0)
    assert out.columns.tolist() == ["Part", "Parts", "Records", "Characters", "Message ID", "Chat"]
    assert out.values.tolist() == [[1, 1, 8, len(telegram.texts()[0]), 4101, "-1001234567890"]]
    assert res.final_message == "8 records sent in 1 message."


def test_table_is_preformatted_so_the_columns_line_up(telegram):
    # The original sent a grid table as plain text, which Telegram shows in a proportional font
    run_block(HERE, SAMPLE, {**SETTINGS, "text_format": "TABLE"}).raise_for_error()
    call = telegram.calls[0]["json"]
    assert call["parse_mode"] == "HTML" and call["text"].startswith("<pre>") and call["text"].endswith("</pre>")
    table = html.unescape(call["text"][5:-6]).split("\n")
    assert table[0] == "Product                | Warehouse | In stock | Reorder level | Last delivery"
    assert set(table[1]) <= {"-", "+"} and len(table) == 10
    assert table[9] == "Fleece & frost cover   | Reading   | 4        | 12            | 2025-02-20"
    assert "Fleece &amp; frost" in call["text"]  # escaped for HTML


def test_json_keeps_numbers_and_writes_dates_as_text(telegram):
    # The original wrote dates as milliseconds since 1970 and missing dates as null via pandas' to_json epoch
    run_block(HERE, SAMPLE, {**SETTINGS, "text_format": "JSON"}).raise_for_error()
    records = json.loads(telegram.texts()[0])
    assert records[0] == {"Product": "Terracotta pot 30cm", "Warehouse": "Leeds", "In stock": 14,
                          "Reorder level": 40, "Last delivery": "2025-03-03"}
    assert records[3]["Last delivery"] is None and len(records) == 8


@pytest.mark.parametrize("form", ["CONCAT", "TABLE", "JSON"])
def test_long_input_is_split_between_records(telegram, form):
    # The original sent one message; Telegram refuses over 4,096 characters ("message is too long"), and the
    # block still finished as if it had worked
    n = 400
    df = pd.DataFrame({"Product": [f"Product {i:03d} <special & co>" for i in range(n)],
                       "Warehouse": ["Leeds"] * n, "In stock": range(n)})
    res = run_block(HERE, df, {**SETTINGS, "text_format": form}).raise_for_error()
    out = res.output(0)
    assert len(out) > 1 and out["Records"].sum() == n and (out["Parts"] == len(out)).all()
    texts = telegram.texts()
    if form == "TABLE":
        bodies = [html.unescape(t[5:-6]).split("\n") for t in texts]
        assert all(b[0].startswith("Product ") for b in bodies)  # the header on every part
        rows = [r for b in bodies for r in b[2:]]
    elif form == "JSON":
        rows = [r["Product"] for t in texts for r in json.loads(t)]
    else:
        rows = [r for t in texts for r in t.split("\n")]
    assert len(rows) == n and "Product 399" in rows[-1]


def test_telegram_refusal_stops_the_block(monkeypatch):
    monkeypatch.setattr(requests, "post", FakeTelegram(chats=()))
    res = run_block(HERE, SAMPLE, SETTINGS)
    assert res.status == "aborted" and "chat not found" in res.final_message
    monkeypatch.setattr(requests, "post", FakeTelegram())
    res = run_block(HERE, SAMPLE, {**SETTINGS, "bot_token": "123:wrong"})
    assert res.status == "aborted" and "Not Found" in res.final_message


def test_network_error_does_not_show_the_token(monkeypatch):
    monkeypatch.setattr(requests, "post", FakeTelegram(network_error=True))
    res = run_block(HERE, SAMPLE, SETTINGS)
    assert res.status == "aborted" and "ConnectionError" in res.final_message and TOKEN not in res.final_message


def test_empty_input_sends_nothing(telegram):
    # The original sent an empty text (or '[]'); Telegram refuses an empty message
    df = pd.DataFrame({"Product": pd.Series([], dtype=object), "In stock": pd.Series([], dtype="int64")})
    for form in ("CONCAT", "TABLE", "JSON"):
        res = run_block(HERE, df, {**SETTINGS, "text_format": form}).raise_for_error()
        assert len(res.output(0)) == 0 and res.final_message == "No records: nothing sent."
    assert telegram.calls == []


def test_missing_settings_stop_before_sending(telegram):
    # The original posted to .../botNone/sendMessage and finished with Telegram's 404 in its output
    for missing, words in (("bot_token", "bot token"), ("chat_id", "chat ID")):
        res = run_block(HERE, SAMPLE, {**SETTINGS, missing: None})
        assert res.status == "aborted" and words in res.final_message
    assert run_block(HERE, None, SETTINGS).status == "aborted"
    assert telegram.calls == []


def test_channel_name_and_types(telegram):
    df = pd.DataFrame({"a": [1, None], "b": [1.5, 2.0], "c": [True, False], "d": ["x", None]})
    run_block(HERE, df, {**SETTINGS, "chat_id": "@stock_alerts"}).raise_for_error()
    assert telegram.texts() == ["1 1.5 True x\n2 False"]
    assert telegram.calls[0]["json"]["chat_id"] == "@stock_alerts"


def test_large_input(telegram):
    n = 20_000
    df = pd.DataFrame({"id": range(n), "name": [f"item {i}" for i in range(n)]})
    t0 = time.time()
    out = run_block(HERE, df, {**SETTINGS, "text_format": "TABLE"}).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert out["Records"].sum() == n and all(c <= 4096 for c in out["Characters"])


def test_emoji_count_twice_towards_the_limit(telegram):
    # Telegram counts UTF-16 code units, so an emoji takes two of the 4,096
    df = pd.DataFrame({"alert": ["\U0001F6A8" * 30 + f" line {i}" for i in range(300)]})
    out = run_block(HERE, df, SETTINGS).raise_for_error().output(0)
    assert len(out) > 1 and out["Records"].sum() == 300 and (out["Characters"] <= 4096).all()
    one = pd.DataFrame({"alert": ["\U0001F6A8" * 3000]})  # 6,000 units in one record: cut
    out = run_block(HERE, one, SETTINGS).raise_for_error().output(0)
    assert 4094 <= out["Characters"][0] <= 4096 and telegram.texts()[-1].endswith("…")
