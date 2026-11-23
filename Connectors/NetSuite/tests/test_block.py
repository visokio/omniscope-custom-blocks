"""Offline contracts: no outbound network calls permitted."""
import importlib.util
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import jwt
import pytest
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


c = load("netsuite_connector", ROOT / "script.py")


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unmocked network call")
    monkeypatch.setattr(requests.sessions.Session, "send", forbidden)


@pytest.fixture(scope="session")
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=3072)


@pytest.fixture
def options(tmp_path, key):
    path = tmp_path / "key.pem"
    path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
    ))
    return dict(service_url="https://demo-sb1.suitetalk.api.netsuite.com", client_id="test-client",
                certificate_id="test-certificate", private_key_file=str(path), private_key_password=None,
                data_mode="saved_search", saved_search_id="customsearch_test", suiteql=None,
                extraction_mode="sample", output_columns=None)


class API:
    def __init__(self, options):
        self.options = options
        self.messages = []
        self.writes = []
        self.commits = []
        self.aborts = []

    def get_option(self, name):
        return self.options.get(name)

    def update_message(self, message):
        self.messages.append(message)

    def write_output(self, frame, output):
        self.writes.append((frame, output))

    def commit(self, message):
        self.commits.append(message)

    def abort(self, message):
        self.aborts.append(message)


class Response:
    def __init__(self, payload=None, status=200, headers=None, raw=None):
        self.status_code = status
        self.headers = headers or {}
        self.body = raw if raw is not None else json.dumps(payload).encode()
        self.closed = False

    def iter_content(self, chunk_size):
        for i in range(0, len(self.body), chunk_size):
            yield self.body[i:i + chunk_size]

    def close(self):
        self.closed = True


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = False
        self.proxies = {}

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response()
        return response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True


class Clock:
    def __init__(self):
        self.value = 0
        self.waits = []

    def now(self):
        return self.value

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.value += seconds


def token(**changes):
    result = {"access_token": "sentinel-token", "token_type": "Bearer", "expires_in": 3600}
    result.update(changes)
    return Response(result)


def page(rows=None, offset=0, total=None, more=False, **changes):
    rows = [{"id": "123"}] if rows is None else rows
    data = dict(items=rows, count=len(rows), offset=offset,
                totalResults=offset + len(rows) if total is None else total, hasMore=more)
    data.update(changes)
    return Response(data)


def execute(options, responses, clock=None):
    api, session = API(options), Session(responses)
    clock = clock or Clock()
    c.run(api, session_factory=lambda: session, clock=clock.now, sleeper=clock.sleep,
          wall_clock=lambda: 1_790_000_000, jitter=lambda: 0)
    return api, session, clock


@pytest.mark.parametrize("mode", ["saved_search", "suiteql"])
def test_requests_and_lifecycle(options, key, mode):
    options.update(data_mode=mode, suiteql=" SELECT id FROM customer ORDER BY id ")
    responses = [token(), page()]
    api, session, _ = execute(options, responses)
    assert not api.aborts
    assert len(api.writes) == len(api.commits) == 1
    assert api.writes[0][1] == "data"
    assert api.writes[0][0].to_dict("records") == [{"id": "123"}]
    assert api.commits == ["Sample: 1 rows, 1 pages; no further rows reported"]
    assert session.closed and all(response.closed for response in responses)
    assert session.trust_env is False
    method, url, kwargs = session.calls[0]
    assert method == "POST" and url.endswith("/services/rest/auth/oauth2/v1/token")
    assert "auth" not in kwargs and "Authorization" not in kwargs["headers"]
    form = kwargs["data"]
    assert form["grant_type"] == "client_credentials"
    assert form["client_assertion_type"] == "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
    assertion = form["client_assertion"]
    assert jwt.get_unverified_header(assertion) == {"alg": "PS256", "kid": "test-certificate", "typ": "JWT"}
    claims = jwt.decode(assertion, key.public_key(), algorithms=["PS256"], audience=url,
                        options={"verify_exp": False, "verify_iat": False})
    assert claims == {"iss": "test-client", "scope": "rest_webservices", "aud": url,
                      "iat": 1_790_000_000, "exp": 1_790_000_300}
    method, url, kwargs = session.calls[1]
    assert kwargs["params"] == {"limit": 100, "offset": 0}
    assert kwargs["headers"]["Authorization"] == "Bearer sentinel-token"
    if mode == "suiteql":
        assert method == "POST" and url.endswith("/services/rest/query/v1/suiteql")
        assert kwargs["headers"]["Prefer"] == "transient"
        assert kwargs["json"] == {"q": options["suiteql"]}
    else:
        assert method == "GET" and url.endswith("/savedsearch/customsearch_test/result")
        assert "json" not in kwargs
    for _, _, kwargs in session.calls:
        assert kwargs["verify"] is True and kwargs["allow_redirects"] is False and kwargs["stream"] is True
        assert kwargs["timeout"] == (10, 120)
    prepared = requests.Request("POST", session.calls[0][1], data=form).prepare()
    assert prepared.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert "urn%3Aietf%3Aparams" in prepared.body


@pytest.mark.parametrize("name,value", [
    ("service_url", "http://demo.suitetalk.api.netsuite.com"),
    ("service_url", "https://demo.suitetalk.api.netsuite.com.evil.example"),
    ("service_url", "https://u@demo.suitetalk.api.netsuite.com"),
    ("service_url", "https://demo.suitetalk.api.netsuite.com/path"),
    ("service_url", "https://demo.suitetalk.api.netsuite.com?secret=x"),
    ("service_url", "https://demo.suitetalk.api.netsuite.com#frag"),
    ("service_url", "https://demo.suitetalk.api.netsuite.com:444"),
    ("service_url", "https://one.two.suitetalk.api.netsuite.com"),
    ("service_url", "https://-bad.suitetalk.api.netsuite.com"),
    ("service_url", "https://127.0.0.1"), ("client_id", ""),
    ("certificate_id", None), ("private_key_file", {}),
    ("data_mode", "soap"), ("extraction_mode", "all"),
    ("saved_search_id", "../x"), ("saved_search_id", "x?foo=1"), ("saved_search_id", ""),
    ("output_columns", "id,,name"), ("output_columns", ",id"), ("output_columns", "[]"),
    ("output_columns", '["id","ID"]'), ("output_columns", '["links"]'),
    ("output_columns", '[""]'), ("output_columns", "[1]"),
])
def test_bad_config_before_network(options, name, value):
    options[name] = value
    api, session, _ = execute(options, [])
    assert len(api.aborts) == 1 and not api.commits and not api.writes and not session.calls


@pytest.mark.parametrize("url", [
    "https://123456.suitetalk.api.netsuite.com/",
    "https://123456-sb1.suitetalk.api.netsuite.com:443/",
    "HTTPS://DEMO.SUITETALK.API.NETSUITE.COM",
])
def test_valid_urls(options, url):
    options["service_url"] = url
    assert c.Config.read(API(options)).service_url.endswith(".suitetalk.api.netsuite.com")


def test_inactive_mode_fields(options):
    options["suiteql"] = {"ignored": True}
    assert c.Config.read(API(options)).suiteql == ""
    options.update(data_mode="suiteql", suiteql="select 1", saved_search_id={"ignored": True})
    assert c.Config.read(API(options)).saved_search_id == ""
    options["suiteql"] = " "
    with pytest.raises(c.ConnectorError):
        c.Config.read(API(options))


@pytest.mark.parametrize("encrypted", [False, True])
def test_private_key(options, tmp_path, key, encrypted):
    password = b" untrimmed sentinel passphrase "
    path = tmp_path / "with spaces.pem"
    path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password) if encrypted else serialization.NoEncryption(),
    ))
    options.update(private_key_file=str(path), private_key_password=password.decode() if encrypted else None)
    assert c.load_key(c.Config.read(API(options))).key_size == 3072
    options["private_key_password"] = "wrong"
    api, session, _ = execute(options, [])
    assert "Invalid key" in api.aborts[0] and not session.calls


@pytest.mark.parametrize("kind", ["invalid", "ec", "small", "missing", "oversized", "4096"])
def test_other_keys(options, tmp_path, kind):
    path = tmp_path / "other.pem"
    options["private_key_file"] = str(path)
    if kind in ("small", "4096", "ec"):
        key = (ec.generate_private_key(ec.SECP256R1()) if kind == "ec"
               else rsa.generate_private_key(public_exponent=65537, key_size=4096 if kind == "4096" else 2048))
        path.write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
        ))
    elif kind != "missing":
        path.write_bytes(b"x" * (65537 if kind == "oversized" else 10))
    api, session, _ = execute(options, [token(), page()])
    assert bool(api.commits) == (kind == "4096")
    assert bool(session.calls) == (kind == "4096")


@pytest.mark.parametrize("changes", [
    {"access_token": None}, {"access_token": ""}, {"access_token": "bad\r\ntoken"},
    {"token_type": "Basic"}, {"token_type": None}, {"expires_in": True}, {"expires_in": 60},
    {"expires_in": "3600"}, {"expires_in": -1},
])
def test_bad_token(options, changes):
    api, session, _ = execute(options, [token(**changes)])
    assert api.aborts and not api.commits and len(session.calls) == 1


def test_full_pages_and_identical_business_rows(options):
    options["extraction_mode"] = "full"
    api, session, _ = execute(options, [
        token(), page([{"id": "same"}] * 1000, total=1001, more=True),
        page([{"id": "same"}], offset=1000, total=1001),
    ])
    assert not api.aborts and len(api.writes[0][0]) == 1001
    assert api.commits[0].startswith("Complete: 1001 rows, 2 pages")
    assert session.calls[-1][2]["params"] == {"limit": 1000, "offset": 1000}


def test_sample_stops_at_one_page(options):
    api, session, _ = execute(options, [token(), page([{"id": i} for i in range(100)], total=200, more=True)])
    assert len(api.writes[0][0]) == 100 and len(session.calls) == 2
    assert "more rows available" in api.commits[0]


@pytest.mark.parametrize("changes", [
    {"items": None}, {"items": [1]}, {"count": True}, {"offset": True}, {"totalResults": True},
    {"count": -1}, {"offset": -1}, {"totalResults": -1}, {"count": 2},
    {"hasMore": 1}, {"hasMore": None}, {"offset": 1000}, {"totalResults": 0},
    {"totalResults": 10}, {"hasMore": True}, {"hasMore": True, "totalResults": 10},
])
def test_bad_paging(options, changes):
    api, _, _ = execute(options, [token(), page(**changes)])
    assert api.aborts and not api.writes and not api.commits


@pytest.mark.parametrize("raw", [
    b'{"items": [], "items": []}', b'{"items": [{"id": 1, "id": 2}]}',
    b'NaN', b'Infinity', b'[]', b'not json', b'{"items":[]}', b'\xff',
])
def test_corrupt_json(options, raw):
    api, _, _ = execute(options, [token(), Response(raw=raw)])
    assert api.aborts and not api.writes


@pytest.mark.parametrize("last", [
    page(offset=0, total=1001), page(offset=1000, total=1002),
    page([], offset=1000, total=1001, more=True),
])
def test_incomplete_second_page(options, last):
    options["extraction_mode"] = "full"
    api, session, _ = execute(options, [token(), page([{}] * 1000, total=1001, more=True), last])
    assert api.aborts and not api.writes and not api.commits and session.closed


def test_oversized_page(options):
    api, _, _ = execute(options, [token(), page([{"id": i} for i in range(101)])])
    assert api.aborts and not api.writes


@pytest.mark.parametrize("status", [400, 403, 404, 301, 500])
def test_no_blind_retry(options, status):
    api, session, _ = execute(options, [token(), Response({"error": "sentinel-secret"}, status)])
    assert len(session.calls) == 2 and api.aborts and not api.commits
    assert "sentinel-secret" not in api.aborts[0]


def test_401_recovers_once(options):
    api, session, _ = execute(options, [token(), Response({}, 401), token(), page()])
    assert api.commits and len(session.calls) == 4
    api, session, _ = execute(options, [token(), Response({}, 401), token(), Response({}, 401)])
    assert api.aborts and len(session.calls) == 4


def test_proactive_renewal(options):
    options["extraction_mode"] = "full"
    clock = Clock()
    def first():
        clock.value = 2
        return page([{}] * 1000, total=1001, more=True)
    api, session, _ = execute(options, [token(expires_in=61), first, token(), page(offset=1000)], clock)
    assert api.commits and len(session.calls) == 4


@pytest.mark.parametrize("failure", [
    Response({}, 429), Response({}, 502), Response({}, 503), Response({}, 504),
    requests.Timeout("sentinel-secret"), requests.ConnectionError("sentinel-secret"),
    requests.exceptions.ChunkedEncodingError("sentinel-secret"),
])
def test_transient_retry(options, failure):
    api, session, clock = execute(options, [token(), failure, page()])
    assert api.commits and len(session.calls) == 3 and clock.waits == [1]


def test_exhaustion_and_combined_recovery(options):
    failures = [Response({}, 503)] * 3
    api, session, clock = execute(options, [token()] + failures)
    assert api.aborts and len(session.calls) == 4 and clock.waits == [1, 2]
    api, session, _ = execute(options, [
        token(), Response({}, 503), Response({}, 401), token(),
        Response({}, 503), Response({}, 503), page(),
    ])
    assert api.commits and len(session.calls) == 7 and len(api.writes[0][0]) == 1


@pytest.mark.parametrize("value,expected", [
    ("10", 10), ("Wed, 21 Oct 2015 07:28:00 GMT", 0), ("nonsense", 1),
])
def test_retry_after(options, value, expected):
    api, _, clock = execute(options, [token(), Response({}, 429, {"Retry-After": value}), page()])
    assert api.commits and clock.waits == [expected]


def test_future_retry_after_date():
    assert c.retry_delay({"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}, 0,
                         lambda: 1445412470, lambda: 0) == 10


def test_limits(options, monkeypatch):
    api, _, _ = execute(options, [token(), Response({}, 429, {"Retry-After": "901"})])
    assert api.aborts and not api.commits
    monkeypatch.setattr(c, "PAGE_BYTES", 20)
    api, session, _ = execute(options, [token()])
    assert api.aborts and session.closed


def test_total_budget_includes_retries(options, monkeypatch):
    first = token()
    error = Response({}, 503, raw=b"x" * 100)
    monkeypatch.setattr(c, "TOTAL_BYTES", len(first.body) + 150)
    api, _, _ = execute(options, [first, error, error])
    assert api.aborts and "size limit" in api.aborts[0]


def test_deadline_and_row_boundary(options, monkeypatch):
    clock = Clock()
    def late():
        clock.value = 901
        return page()
    api, _, _ = execute(options, [token(), late], clock)
    assert api.aborts and not api.writes
    options["extraction_mode"] = "full"
    api, _, _ = execute(options, [token(), page([{}] * 1000, total=100000, more=True)])
    assert api.aborts and not api.writes
    monkeypatch.setattr(c, "ROW_LIMIT", 1)
    api, _, _ = execute(options, [token(), page()])
    assert api.aborts and not api.writes


def test_text_null_and_nested_precision():
    rows = c.decode_json(
        '[{"links":[],"id":123456789012345678901234567890,"amount":123.456789012345678901,'
        '"blank":"","missing":null,"literal":"null","bool":true,"unicode":"é",'
        '"nested":{"links":[],"id":123456789012345678901}},{"late":[1,null,{"x":2}]}]'
    )
    frame = c.make_frame(rows, None)
    assert list(frame.columns) == sorted((set(rows[0]) | {"late"}) - {"links"})
    assert "links" not in frame.columns and list(frame.columns) == sorted(frame.columns)
    first = frame.to_dict("records")[0]
    assert first["id"] == "123456789012345678901234567890"
    assert first["amount"] == "123.456789012345678901"
    assert first["blank"] is None and first["missing"] is None and first["literal"] == "null"
    assert first["bool"] == "true" and first["unicode"] == "é" and first["late"] is None
    assert first["nested"] == '{"links":[],"id":123456789012345678901}'
    assert frame.to_dict("records")[1]["late"] == '[1,null,{"x":2}]'
    assert c.text_value(False) == "false"
    assert c.text_value(Decimal("1E+999")) == "1E+999"
    assert c.text_value({"empty": ""}) == '{"empty":""}'


@pytest.mark.parametrize("rows", [[{"": "x"}], [{"id": "1"}, {"ID": "2"}], [{" id ": "1"}]])
def test_column_collisions(rows):
    with pytest.raises(c.ConnectorError):
        c.make_frame(rows, None)


@pytest.mark.parametrize("fields", ['id, name', '["id", "name"]'])
def test_explicit_columns(options, fields):
    options["output_columns"] = fields
    api, _, _ = execute(options, [token(), page([])])
    assert api.commits and list(api.writes[0][0].columns) == ["id", "name"]
    assert len(api.writes[0][0]) == 0
    api, _, _ = execute(options, [token(), page([{"id": "1"}])])
    assert api.writes[0][0].to_dict("records") == [{"id": "1", "name": None}]
    api, _, _ = execute(options, [token(), page([{"extra": "1"}])])
    assert api.commits and api.writes[0][0].to_dict("records") == [{"id": None, "name": None}]
    options["output_columns"] = None
    api, _, _ = execute(options, [token(), page([])])
    assert api.aborts and "Output fields" in api.aborts[0]


def test_secrets_do_not_escape(options, capsys):
    options["suiteql"] = "sentinel-query"
    api, _, _ = execute(options, [token(), Response({"detail": "sentinel-response"}, 400)])
    output = repr(api.messages + api.aborts + api.commits) + capsys.readouterr().out + capsys.readouterr().err
    for sentinel in ("sentinel-token", "sentinel-query", "sentinel-response", options["private_key_file"]):
        assert sentinel not in output
    api, _, _ = execute(options, [token(), RuntimeError("sentinel-unexpected")])
    assert "sentinel-unexpected" not in api.aborts[0]


def test_safe_error_code_and_tls(options):
    api, _, _ = execute(options, [Response({"error": "invalid_grant"}, 400)])
    assert "invalid_grant" in api.aborts[0]
    api, session, _ = execute(options, [requests.exceptions.SSLError("sentinel-secret")])
    assert len(session.calls) == 1 and "TLS" in api.aborts[0] and "sentinel-secret" not in api.aborts[0]


def test_endpoint_allowlist(options, key):
    session = Session([])
    client = c.Client(c.Config.read(API(options)), key, session, c.Budget(), lambda _: None)
    with pytest.raises(c.ConnectorError):
        client.request("DELETE", "/services/rest/record/v1/customer/1", "Data", {}, lambda: {})
    assert not session.calls


def test_import_is_inert_and_python39_syntax():
    import ast
    ast.parse((ROOT / "script.py").read_text(), feature_version=(3, 9))
    # Omniscope is deliberately not installed; importing must neither connect nor execute.
    result = subprocess.run([sys.executable, "-c",
                             "import runpy; runpy.run_path(" + repr(str(ROOT / "script.py")) + ")"],
                            capture_output=True, timeout=10)
    assert result.returncode == 0 and result.stdout == b"" and result.stderr == b""


def test_single_api_instance_and_watchdog(monkeypatch):
    import types
    api = types.ModuleType("omniscope.api")
    instances = []
    api.OmniscopeApi = lambda: instances.append(object()) or instances[-1]
    monkeypatch.setitem(sys.modules, "omniscope", types.ModuleType("omniscope"))
    monkeypatch.setitem(sys.modules, "omniscope.api", api)
    seen = []
    monkeypatch.setattr(c, "run", lambda obj: seen.append(obj))
    c.main()
    assert len(instances) == 1 and seen == instances
    # A stuck transport cannot turn the overall deadline into an indefinite wait.
    code = """
import runpy, types, sys, time
m = runpy.run_path(PATH)
api = types.ModuleType('omniscope.api')
api.OmniscopeApi = lambda: None
sys.modules['omniscope'] = types.ModuleType('omniscope')
sys.modules['omniscope.api'] = api
m['main'].__globals__['EXECUTION_SECONDS'] = 0.1
m['main'].__globals__['run'] = lambda _: time.sleep(60)
m['main']()
""".replace("PATH", repr(str(ROOT / "script.py")))
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=10)
    assert result.returncode == 1 and b"extract incomplete" in result.stderr


def test_manifest_contract():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    assert manifest["optionsVersion"] == 1
    assert manifest["apiVersion"] == "VERSION_0"
    assert manifest["apiMode"] == "BATCH"
    assert manifest["language"] == "PYTHON"
    assert manifest["scriptFilename"] == "script.py"
    assert manifest["category"] == "Connectors"
    assert not manifest.get("blockInputs")
    assert [(out["id"], out["label"]) for out in manifest["blockOutputs"]] == [("data", "Data")]
    expected = {
        "service_url": "Text", "client_id": "Text", "certificate_id": "Text", "private_key_file": "File",
        "private_key_password": "Password", "data_mode": "Choice", "saved_search_id": "Text",
        "suiteql": "Text", "extraction_mode": "Choice", "output_columns": "Text",
    }
    assert [option["name"] for option in manifest["options"]] == list(expected)
    for option in manifest["options"]:
        name = option["name"]
        assert option["@visokiotype"] == "CustomBlockSchema." + expected[name] + "CustomBlockPublicOption"
        if name in ("data_mode", "extraction_mode"):
            choices = ["saved_search", "suiteql"] if name == "data_mode" else ["sample", "full"]
            assert [choice["value"] for choice in option["choices"]] == choices
            assert option["defaultValue"] == choices[0]
        else:
            assert option.get("defaultValue") is None
        if name == "private_key_file":
            assert option["readOnly"] is True
    assert manifest["docker"]["useCustomBaseImage"] is False


@pytest.mark.parametrize("fields", [None, "", "   "])
def test_all_fields_by_default(options, fields):
    options["output_columns"] = fields
    api, _, _ = execute(options, [token(), page([{"id": "1", "name": "Example", "extra": "yes"}])])
    assert api.commits
    assert api.writes[0][0].to_dict("records") == [{"extra": "yes", "id": "1", "name": "Example"}]


def test_field_selection_order(options):
    options["output_columns"] = " name, id "
    api, _, _ = execute(options, [token(), page([{"id": "1", "name": "Example", "extra": "ignored"}])])
    assert api.commits and list(api.writes[0][0].columns) == ["name", "id"]
    assert api.writes[0][0].to_dict("records") == [{"name": "Example", "id": "1"}]


@pytest.mark.parametrize("mode", ["saved_search", "suiteql"])
def test_repository_harness(monkeypatch, options, mode):
    from harness.runner import run_block
    import pandas as pd

    rows = [{"id": "123456789012345678901", "name": "Example", "amount": "123.45"}]
    replies = [token(), page(rows)]
    calls = []

    def request(session, method, url, **kwargs):
        calls.append((method, url))
        return replies.pop(0)

    monkeypatch.setattr(requests.Session, "request", request)
    options.update(data_mode=mode, suiteql="SELECT id FROM customer ORDER BY id")
    # Exercise defaults from the real manifest, main(), and the shared output API without upstream input.
    del options["extraction_mode"]
    result = run_block(ROOT, options=options).raise_for_error()
    assert result.output(0).to_dict("records") == [{"amount": "123.45", "id": rows[0]["id"], "name": "Example"}]
    assert all(pd.api.types.is_string_dtype(result.output(0)[name]) for name in result.output(0))
    assert result.final_message == "Sample: 1 rows, 1 pages; no further rows reported"
    assert len(calls) == 2 and not replies


def test_repository_harness_empty_and_failure(monkeypatch, options):
    from harness.runner import run_block

    replies = [token(), page([])]
    monkeypatch.setattr(requests.Session, "request", lambda *args, **kwargs: replies.pop(0))
    options["output_columns"] = "id, name"
    result = run_block(ROOT, options=options).raise_for_error()
    assert list(result.output(0).columns) == ["id", "name"] and result.output(0).empty
    replies.extend([token(), Response(status=403, raw=b"sentinel-private-response")])
    result = run_block(ROOT, options=options)
    assert result.status == "aborted" and not result.outputs
    assert "sentinel-private-response" not in str(result.messages) + str(result.final_message)
