"""Tests for the AI Chat - Google Gemini block.

No request ever reaches Google. Most tests replace the google-genai package with a stand-in that checks each request
and answers from the canned payloads in tests/canned/. The last tests, which run only when the real google-genai
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
SAMPLE = os.path.join(HERE, "sample-data", "supplier-descriptions.csv")
OPTIONS = {"GEMINI_API_KEY": "AIza-fake", "Prompt": "Description", "SystemPrompt": "Instruction"}


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


def install(monkeypatch, service):
    """Replace google.genai with a stand-in for its Client.models.generate_content."""
    envelope = canned("generate-content.json")

    def config_dict(config):
        if config is None:
            return {}
        if isinstance(config, dict):
            return dict(config)
        return {k: v for k, v in vars(config).items() if v is not None}

    class Models:
        def generate_content(self, *, model, contents, config=None):
            request = dict(model=model, contents=contents, config=config_dict(config))
            service.requests.append(copy.deepcopy(request))
            system = request["config"].get("system_instruction")
            if system is not None and not isinstance(system, str):
                raise APIError(400, "Invalid system_instruction")
            reply, truncated = service.answer(contents)
            body = filled(envelope, reply, "MAX_TOKENS" if truncated else "STOP")
            candidate = body["candidates"][0]
            text = "".join(part.get("text", "") for part in candidate["content"]["parts"])
            return SimpleNamespace(text=text, candidates=[SimpleNamespace(finish_reason=candidate["finishReason"])])

    class Client:
        def __init__(self, api_key=None, **kwargs):
            service.clients.append(dict(api_key=api_key, **kwargs))
            self.models = Models()

    class GenerateContentConfig(SimpleNamespace):
        pass

    genai = types.ModuleType("google.genai")
    genai.Client = Client
    genai.types = types.ModuleType("google.genai.types")
    genai.types.GenerateContentConfig = GenerateContentConfig
    google = types.ModuleType("google")
    google.genai = genai
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai.types)
    return service


def system_of(request):
    system = request["config"].get("system_instruction")
    return [system] if system else []


def prompt_of(request):
    return request["contents"]


@pytest.fixture
def service(monkeypatch):
    return install(monkeypatch, Service())


def run(inputs, options=None, **kw):
    return run_block(HERE, inputs, {**OPTIONS, **(options or {})}, **kw)


def frame(prompts, **extra):
    return pd.DataFrame({"Id": list(range(1, len(prompts) + 1)), "Description": prompts, **extra})


# ------------------------------------------------------------------------------------------ the sample


def test_sample_gets_one_reply_per_record(service):
    res = run(SAMPLE).raise_for_error()
    out = res.output(0)
    sample = pd.read_csv(SAMPLE)
    assert len(out) == 10
    assert list(out.columns) == list(sample.columns) + ["Response", "Truncated"]
    by_key = dict(zip(out["SKU"], out["Response"]))
    assert by_key["GS-1003"] == "Biodegradable Coir Plant Pots, 8 cm, Pack of 50"
    assert not out["Truncated"].fillna(False).any()
    # every reply sits on the record whose prompt produced it
    for prompt, reply in zip(out["Description"], out["Response"]):
        if isinstance(prompt, str):
            assert reply == REPLIES[prompt]
    # the instruction field went as the system prompt, the prompt field as the user message
    assert len(service.requests) == 10
    assert all(system_of(r) == [sample["Instruction"][0]] for r in service.requests)
    assert {prompt_of(r) for r in service.requests} == set(REPLIES)
    assert res.final_message.startswith("10 responses received")


def test_default_request(service):
    run(frame(["Hello"]), {"SystemPrompt": None}).raise_for_error()
    (client,) = service.clients
    assert client["api_key"] == "AIza-fake"

    (request,) = service.requests
    assert request["model"] == "gemini-3.5-flash-lite"
    assert request["contents"] == "Hello"
    assert request["config"] == {}  # no temperature, system instruction or length limit unless set


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
    assert list(out.columns) == ["Id", "Description", "Region", "Amount", "Response", "Truncated"]
    assert out["Id"].tolist() == [1] and out["Amount"].tolist() == [12.5]


def test_existing_response_field_is_not_overwritten(service):
    df = frame(["Hello"], Response=["earlier answer"])
    out = run(df, {"SystemPrompt": None}).raise_for_error().output(0)
    assert out["Response"].tolist() == ["earlier answer"]
    assert out["Response 2"].tolist() == ["Reply to: Hello"] and "Truncated 2" in out.columns


def test_empty_input_keeps_the_fields(service):
    # The original wrote a frame with no fields at all
    df = pd.DataFrame({"Id": pd.Series([], dtype="int64"), "Description": pd.Series([], dtype=object)})
    out = run(df, {"SystemPrompt": None}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["Id", "Description", "Response", "Truncated"]
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
    res = run(df, {"GEMINI_API_KEY": None, "SystemPrompt": None})
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
    res = run(df, {"Temperature": 2.5, "SystemPrompt": None})
    assert res.status == "aborted" and "Temperature" in res.final_message
    assert service.requests == []


def test_temperature_and_length_limit_are_sent_only_when_set(service):
    # The original always sent temperature 0.5; Google recommends the default (1.0) for Gemini 3 models
    run(frame(["Hello"]), {"SystemPrompt": None}).raise_for_error()
    run(frame(["Hello"]), {"SystemPrompt": None, "Temperature": 1.2, "MaxTokens": 64}).raise_for_error()
    first, second = service.requests
    assert "temperature" not in first["config"]
    assert second["config"] == {"temperature": 1.2, "max_output_tokens": 64}


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
    prompt = body["contents"][0]["parts"][0]["text"]
    return filled(canned("generate-content.json"), REPLIES.get(prompt, "Reply to: " + prompt), finish or "STOP")


def test_real_sdk_request_and_reply(http):
    pytest.importorskip("google.genai")
    out = run(SAMPLE, {"Temperature": 0.2, "MaxTokens": 80}).raise_for_error().output(0)
    assert [r for r in out["Response"] if isinstance(r, str)] == list(REPLIES.values())
    assert not out["Truncated"].any()
    first = http.seen[0]
    assert first["url"].startswith("https://generativelanguage.googleapis.com/")
    assert first["url"].endswith("/models/gemini-3.5-flash-lite:generateContent")
    assert first["headers"]["x-goog-api-key"] == "AIza-fake"
    body = first["body"]
    assert body["systemInstruction"]["parts"][0]["text"].startswith("Write a product title")
    assert body["generationConfig"] == {"temperature": 0.2, "maxOutputTokens": 80}


def test_real_sdk_truncated_reply_is_flagged(http):
    pytest.importorskip("google.genai")
    http.state["finish"] = "MAX_TOKENS"
    out = run(SAMPLE, {"Concurrency": 1}).raise_for_error().output(0)
    assert out["Truncated"].all()


def test_real_sdk_error_reply(http):
    pytest.importorskip("google.genai")
    http.state.update(status=400, body=canned("error-400-api-key.json"))
    res = run(SAMPLE, {"Concurrency": 1})
    assert res.status == "aborted" and "API key not valid" in res.final_message
