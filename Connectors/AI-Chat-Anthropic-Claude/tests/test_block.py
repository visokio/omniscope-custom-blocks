"""Tests for the AI Chat - Claude block.

No request ever reaches Anthropic. Most tests replace the anthropic package with a stand-in that checks each request
and answers from the canned payloads in tests/canned/. The last tests, which run only when the real anthropic
package is installed, let the real client build each HTTP request and answer it from the same canned payloads
by replacing the HTTP client's send method, so the request body and the parsing of the reply are the real ones.
"""
import copy
import json
import os
import sys
import time
import types
from types import SimpleNamespace

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
SAMPLE = os.path.join(HERE, "sample-data", "support-emails.csv")
OPTIONS = {"AnthropicApiKey": "sk-ant-fake", "Prompt": "Message", "SystemPrompt": "Instruction"}


def canned(name):
    with open(os.path.join(CANNED, name), encoding="utf-8") as fh:
        return json.load(fh)


REPLIES = canned("sample-replies.json")["replies"]


def ns(value):
    """JSON to attribute access, like the SDK's response objects."""
    if isinstance(value, dict):
        return SimpleNamespace(**{k: ns(v) for k, v in value.items()})
    if isinstance(value, list):
        return [ns(v) for v in value]
    return value


def filled(payload, reply, finish):
    """A canned payload with the reply text and finish reason put in."""
    text = json.dumps(payload).replace("__REPLY__", json.dumps(reply)[1:-1]).replace("__FINISH__", finish)
    return json.loads(text)


class APIError(Exception):
    """Stands in for the SDK's error classes, which carry the HTTP status."""

    def __init__(self, status, message):
        super().__init__(f"Error code: {status} - {message}")
        self.status_code = status


class Service:
    """What the stand-in SDK answers: the sample replies, or "Reply to: <prompt>"."""

    def __init__(self, delay=0.0, fail_on=None, fail_status=401, truncate=()):
        self.delay, self.fail_on, self.fail_status, self.truncate = delay, fail_on, fail_status, set(truncate)
        self.clients, self.requests = [], []

    def answer(self, prompt):
        if not isinstance(prompt, str) or not prompt:
            raise APIError(400, "Invalid type for the message content: expected a non-empty string.")
        if self.delay:
            time.sleep(self.delay)
        if prompt == self.fail_on:
            raise APIError(self.fail_status, "invalid api key")
        return REPLIES.get(prompt, "Reply to: " + prompt), prompt in self.truncate


def install(monkeypatch, service, payload="message.json"):
    """Replace the anthropic package with a stand-in for its Messages client (SDK 2.x signature)."""
    envelope = canned(payload)

    class Messages:
        def create(self, *, model, max_tokens, messages, system=None, **rest):
            if rest:  # SDK 2.x has no temperature, top_p or top_k: the real method raises TypeError
                raise TypeError(f"create() got unexpected keyword arguments: {sorted(rest)}")
            request = dict(model=model, max_tokens=max_tokens, messages=messages)
            if system is not None:
                request["system"] = system
            service.requests.append(copy.deepcopy(request))
            if system is not None and not isinstance(system, str):
                raise APIError(400, "system: Input should be a valid string")
            content = messages[-1]["content"]
            prompt = content if isinstance(content, str) else content[0]["text"]
            reply, truncated = service.answer(prompt)
            return ns(filled(envelope, reply, "max_tokens" if truncated else "end_turn"))

    class Anthropic:
        def __init__(self, api_key=None, **kwargs):
            service.clients.append(dict(api_key=api_key, **kwargs))
            self.messages = Messages()

    module = types.ModuleType("anthropic")
    module.Anthropic = Anthropic
    monkeypatch.setitem(sys.modules, "anthropic", module)
    return service


def system_of(request):
    return [request["system"]] if "system" in request else []


def prompt_of(request):
    content = request["messages"][-1]["content"]
    return content if isinstance(content, str) else content[0]["text"]


@pytest.fixture
def service(monkeypatch):
    return install(monkeypatch, Service())


def run(inputs, options=None, **kw):
    return run_block(HERE, inputs, {**OPTIONS, **(options or {})}, **kw)


def frame(prompts, **extra):
    return pd.DataFrame({"Id": list(range(1, len(prompts) + 1)), "Message": prompts, **extra})


# ------------------------------------------------------------------------------------------ the sample


def test_sample_gets_one_reply_per_record(service):
    res = run(SAMPLE).raise_for_error()
    out = res.output(0)
    sample = pd.read_csv(SAMPLE)
    assert len(out) == 10
    assert list(out.columns) == list(sample.columns) + ["Response", "Truncated"]
    by_key = dict(zip(out["Ticket"], out["Response"]))
    assert by_key["T-4103"] == "Billing" and by_key["T-4108"] == "Product fault"
    assert pd.isna(by_key["T-4106"])  # empty message: not sent
    assert not out["Truncated"].fillna(False).any()
    # every reply sits on the record whose prompt produced it
    for prompt, reply in zip(out["Message"], out["Response"]):
        if isinstance(prompt, str):
            assert reply == REPLIES[prompt]
    # the instruction field went as the system prompt, the prompt field as the user message
    assert len(service.requests) == 9
    assert all(system_of(r) == [sample["Instruction"][0]] for r in service.requests)
    assert {prompt_of(r) for r in service.requests} == set(REPLIES)
    assert res.final_message.startswith("9 responses received")


def test_default_request(service):
    run(frame(["Hello"]), {"SystemPrompt": None}).raise_for_error()
    (client,) = service.clients
    assert client["api_key"] == "sk-ant-fake"

    (request,) = service.requests
    assert request["model"] == "claude-haiku-5-5"
    assert request["max_tokens"] == 1024 and "system" not in request
    assert request["messages"] == [{"role": "user", "content": "Hello"}]


# ------------------------------------------------------------------------------------------ the fixes


def test_system_prompt_field_is_optional(service):
    # The original read row[None] when no system prompt field was chosen, and failed with KeyError
    out = run(frame(["Hello", "Bye"]), {"SystemPrompt": None}).raise_for_error().output(0)
    assert out["Response"].tolist() == ["Reply to: Hello", "Reply to: Bye"]
    assert all(system_of(r) == [] for r in service.requests)


def test_missing_prompts_are_not_sent(service):
    # The original sent missing values (NaN) to the service, which rejects them, so the block failed
    df = frame(["Hello", None, "  ", "Bye"])
    out = run(df, {"SystemPrompt": None}).raise_for_error().output(0)
    assert [prompt_of(r) for r in service.requests] == ["Hello", "Bye"]
    assert out["Response"].iloc[0] == "Reply to: Hello" and out["Response"].iloc[3] == "Reply to: Bye"
    assert out["Response"].iloc[1:3].isna().all() and out["Truncated"].iloc[1:3].isna().all()


def test_numbers_and_dates_are_sent_as_text(service):
    # The original sent numbers as numbers; the service expects text and rejects them
    df = pd.DataFrame({"Id": [1, 2, 3], "Code": [42, None, 7]})  # whole numbers arrive as Int64
    out = run(df, {"Prompt": "Code", "SystemPrompt": None}).raise_for_error().output(0)
    assert [prompt_of(r) for r in service.requests] == ["42", "7"]
    assert out["Response"].tolist()[0] == "Reply to: 42"
    df = pd.DataFrame({"When": ["2025-03-01"], "Rate": [1.5]})
    run(df, {"Prompt": "When", "SystemPrompt": "Rate"}).raise_for_error()
    assert prompt_of(service.requests[-1]).startswith("2025-03-01") and system_of(service.requests[-1]) == ["1.5"]


def test_input_fields_are_kept(service):
    # The original output only Prompt, System Prompt and Response, so the reply could not be joined back
    df = frame(["Hello"], Region=["North"], Amount=[12.5])
    out = run(df, {"SystemPrompt": None}).raise_for_error().output(0)
    assert list(out.columns) == ["Id", "Message", "Region", "Amount", "Response", "Truncated"]
    assert out["Id"].tolist() == [1] and out["Amount"].tolist() == [12.5]


def test_existing_response_field_is_not_overwritten(service):
    df = frame(["Hello"], Response=["earlier answer"])
    out = run(df, {"SystemPrompt": None}).raise_for_error().output(0)
    assert out["Response"].tolist() == ["earlier answer"]
    assert out["Response 2"].tolist() == ["Reply to: Hello"] and "Truncated 2" in out.columns


def test_empty_input_keeps_the_fields(service):
    # The original wrote a frame with no fields at all
    df = pd.DataFrame({"Id": pd.Series([], dtype="int64"), "Message": pd.Series([], dtype=object)})
    out = run(df, {"SystemPrompt": None}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["Id", "Message", "Response", "Truncated"]
    assert service.clients == [] and service.requests == []


def test_truncated_replies_are_flagged(monkeypatch):
    service = install(monkeypatch, Service(truncate={"Long one"}))
    res = run(frame(["Short", "Long one"]), {"SystemPrompt": None}).raise_for_error()
    assert res.output(0)["Truncated"].tolist() == [False, True]
    assert "1 response cut short at the maximum length" in res.final_message
    assert len(service.requests) == 2


def test_failed_request_stops_with_a_clear_message(monkeypatch):
    # The original raised the SDK's exception, with no record number or hint
    install(monkeypatch, Service(fail_on="Third"))
    res = run(frame(["First", "Second", "Third"]), {"SystemPrompt": None, "Concurrency": 1})
    assert res.status == "aborted" and res.error is None
    assert "record 3" in res.final_message and "Check the API key" in res.final_message
    assert res.output(0) is None
    install(monkeypatch, Service(fail_on="First", fail_status=404))
    res = run(frame(["First"]), {"SystemPrompt": None})
    assert res.status == "aborted" and "Check the model name" in res.final_message


def test_large_input_is_sent_several_at_a_time(monkeypatch):
    # 400 records at 10 ms each: about 4 s one at a time, about 0.5 s eight at a time
    service = install(monkeypatch, Service(delay=0.01))
    prompts = [f"Question {i}" for i in range(400)]
    start = time.perf_counter()
    res = run(frame(prompts), {"SystemPrompt": None, "Concurrency": 8}).raise_for_error()
    elapsed = time.perf_counter() - start
    out = res.output(0)
    assert out["Response"].tolist() == ["Reply to: " + p for p in prompts]  # order kept
    assert len(service.requests) == 400 and elapsed < 2.5
    assert any("Received" in m for m in res.messages)


# ------------------------------------------------------------------------------------------ option checks


def test_option_checks(service):
    df = frame(["Hello"])
    assert run(None).status == "aborted"
    res = run(df, {"AnthropicApiKey": None, "SystemPrompt": None})
    assert res.status == "aborted" and "API key" in res.final_message
    res = run(df, {"Prompt": None, "SystemPrompt": None})
    assert res.status == "aborted" and "User prompt field" in res.final_message
    res = run(df, {"Prompt": "Nope", "SystemPrompt": None})
    assert res.status == "aborted" and "'Nope'" in res.final_message
    res = run(df, {"SystemPrompt": "Missing"})
    assert res.status == "aborted" and "System prompt field" in res.final_message
    res = run(df, {"Model": "  ", "SystemPrompt": None})
    assert res.status == "aborted" and "model" in res.final_message
    res = run(df, {"MaxTokens": 0, "SystemPrompt": None})
    assert res.status == "aborted" and "at least 1" in res.final_message
    assert service.requests == []


def test_no_temperature_is_sent(service):
    # The original always passed temperature; the anthropic SDK 2.x has no such parameter (TypeError), and the API
    # rejects it for current models. The option is gone from the manifest.
    import json as _json
    with open(os.path.join(HERE, "manifest.json"), encoding="utf-8") as fh:
        names = [o["name"] for o in _json.load(fh)["options"]]
    assert "Temperature" not in names
    run(frame(["Hello"]), {"SystemPrompt": None, "MaxTokens": 300}).raise_for_error()
    (request,) = service.requests
    assert "temperature" not in request and request["max_tokens"] == 300


def test_reply_after_a_thinking_block(monkeypatch):
    # The original took content[0].text, which is not the reply when the model returns a thinking block first
    install(monkeypatch, Service(), payload="message-with-thinking.json")
    out = run(frame(["Hello"]), {"SystemPrompt": None}).raise_for_error().output(0)
    assert out["Response"].tolist() == ["Reply to: Hello"]


def test_reply_with_no_text(monkeypatch):
    # A reply with no content blocks (a refusal) made the original fail with IndexError
    install(monkeypatch, Service(), payload="message-refusal.json")
    out = run(frame(["Hello"]), {"SystemPrompt": None}).raise_for_error().output(0)
    assert out["Response"].tolist() == [""] and out["Truncated"].tolist() == [False]


# ------------------------------------------------------------------------------------------ the real SDK


@pytest.fixture
def http(monkeypatch):
    """Answer every HTTP request the real SDK makes from the canned payloads; nothing leaves the machine."""
    seen = []
    state = {"status": 200, "body": None, "finish": None}

    def make_send(module):
        def send(self, request, *args, **kwargs):
            body = json.loads(request.content or b"{}")
            seen.append({"url": str(request.url), "headers": dict(request.headers), "body": body})
            if state["status"] != 200:
                return module.Response(state["status"], json=state["body"], request=request)
            return module.Response(200, json=reply_body(body, state["finish"]), request=request)
        return send

    patched = 0
    for name in ("httpx", "httpx2"):
        try:
            module = __import__(name)
        except ImportError:
            continue
        monkeypatch.setattr(module.Client, "send", make_send(module))
        patched += 1
    if not patched:
        pytest.skip("no HTTP client library installed")
    return SimpleNamespace(seen=seen, state=state)


def reply_body(body, finish=None):
    prompt = body["messages"][-1]["content"]
    prompt = prompt if isinstance(prompt, str) else prompt[0]["text"]
    return filled(canned("message.json"), REPLIES.get(prompt, "Reply to: " + prompt), finish or "end_turn")


def test_real_sdk_request_and_reply(http):
    pytest.importorskip("anthropic")
    out = run(SAMPLE).raise_for_error().output(0)
    assert [r for r in out["Response"] if isinstance(r, str)] == list(REPLIES.values())
    first = http.seen[0]
    assert first["url"] == "https://api.anthropic.com/v1/messages"
    # SDK 2.x sends the key as a bearer token (API version 2026-10-21); earlier versions as x-api-key
    assert "sk-ant-fake" in (first["headers"].get("x-api-key"), first["headers"].get("authorization", "")[7:])
    body = first["body"]
    assert body["model"] == "claude-haiku-5-5" and body["max_tokens"] == 1024
    assert body["system"].startswith("You triage") and body["messages"][0]["role"] == "user"
    assert "temperature" not in body


def test_real_sdk_truncated_reply_is_flagged(http):
    pytest.importorskip("anthropic")
    http.state["finish"] = "max_tokens"
    out = run(SAMPLE, {"Concurrency": 1}).raise_for_error().output(0)
    assert out["Truncated"].dropna().all() and out["Truncated"].notna().sum() == len(REPLIES)


def test_real_sdk_error_reply(http):
    pytest.importorskip("anthropic")
    http.state.update(status=401, body=canned("error-401.json"))
    res = run(SAMPLE, {"Concurrency": 1})
    assert res.status == "aborted" and "AuthenticationError" in res.final_message
    assert "Check the API key" in res.final_message
