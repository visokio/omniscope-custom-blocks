"""NetSuite Connector v0.1.0. Read-only; awaiting live NetSuite validation."""

import math
import os
import random
import re
import threading
import time
from dataclasses import dataclass
from decimal import Decimal
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import jwt
import pandas as pd
import requests
import simplejson as json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


VERSION = "0.1.0"
TOKEN_PATH = "/services/rest/auth/oauth2/v1/token"
QUERY_PATH = "/services/rest/query/v1/suiteql"
ROW_LIMIT = 100_000
PAGE_BYTES = 8 * 1024 * 1024
TOTAL_BYTES = 64 * 1024 * 1024
EXECUTION_SECONDS = 15 * 60
RENEW_SECONDS = 60
TRANSIENT = {429, 502, 503, 504}
SAFE_CODES = {
    "invalid_grant", "invalid_client", "invalid_scope", "INVALID_LOGIN",
    "INVALID_LOGIN_ATTEMPT", "INSUFFICIENT_PERMISSION", "INVALID_PARAMETER",
    "INVALID_QUERY", "INVALID_SEARCH", "NONEXISTENT_ID", "CONCURRENCY_LIMIT_EXCEEDED",
    "SSS_REQUEST_LIMIT_EXCEEDED",
}
OPTION_NAMES = (
    "service_url", "client_id", "certificate_id", "private_key_file", "private_key_password",
    "data_mode", "saved_search_id", "suiteql", "extraction_mode", "output_columns",
)


class ConnectorError(Exception):
    """Only constant, intentionally safe messages may cross the UI boundary."""


def fail(message):
    raise ConnectorError(message)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("Unexpected response: duplicate JSON keys.")
        result[key] = value
    return result


def decode_json(body):
    try:
        return json.loads(body, use_decimal=True, object_pairs_hook=unique_object, allow_nan=False)
    except (ValueError, UnicodeError, RecursionError):
        fail("Unexpected response: invalid JSON.")


def validate_columns(columns):
    if not isinstance(columns, list) or not columns:
        fail("Invalid configuration: Output fields must contain at least one field name.")
    seen = set()
    for name in columns:
        if (
            not isinstance(name, str) or not name.strip() or name != name.strip()
            or name.casefold() in seen or name == "links"
        ):
            fail("Invalid columns: use distinct nonempty names without surrounding spaces; links is reserved.")
        seen.add(name.casefold())
    return columns


@dataclass(repr=False)
class Config:
    service_url: str
    client_id: str
    certificate_id: str
    private_key_file: str
    private_key_password: object
    data_mode: str
    saved_search_id: str
    suiteql: str
    extraction_mode: str
    output_columns: object

    @classmethod
    def read(cls, api):
        values = {name: api.get_option(name) for name in OPTION_NAMES}
        for name in ("service_url", "client_id", "certificate_id", "private_key_file"):
            if not isinstance(values[name], str) or not values[name].strip():
                fail("Invalid configuration: specify the connection URL, client ID, certificate ID and key file.")
        for name in ("service_url", "client_id", "certificate_id"):
            values[name] = values[name].strip()
        # Match the complete origin, not a substring or an arbitrary URL supplied by a response.
        match = re.fullmatch(
            r"https://([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.suitetalk\.api\.netsuite\.com)"
            r"(?::443)?/?", values["service_url"], re.IGNORECASE,
        )
        if not match:
            fail("Invalid configuration: use the HTTPS account-specific SuiteTalk origin from Company URLs.")
        values["service_url"] = "https://" + match.group(1).lower()
        if values["private_key_password"] is not None and not isinstance(values["private_key_password"], str):
            fail("Invalid configuration: the private-key password must be text.")
        if values["data_mode"] not in ("saved_search", "suiteql"):
            fail("Invalid configuration: choose Saved search or SuiteQL.")
        if values["extraction_mode"] not in ("sample", "full"):
            fail("Invalid configuration: choose Sample or Full.")
        if values["data_mode"] == "saved_search":
            value = values["saved_search_id"]
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value.strip()):
                fail("Invalid configuration: specify a saved-search ID using letters, digits, underscores or hyphens.")
            values["saved_search_id"] = value.strip()
            values["suiteql"] = ""
        else:
            if not isinstance(values["suiteql"], str) or not values["suiteql"].strip():
                fail("Invalid configuration: specify a SuiteQL query.")
            values["saved_search_id"] = ""
        raw = values["output_columns"]
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            values["output_columns"] = None
        else:
            if not isinstance(raw, str):
                fail("Invalid configuration: Output fields must be comma-separated text.")
            try:
                # Accept the original JSON format for existing block configurations.
                fields = decode_json(raw) if raw.lstrip().startswith("[") else [v.strip() for v in raw.split(",")]
                values["output_columns"] = validate_columns(fields)
            except ConnectorError:
                fail("Invalid configuration: Output fields must contain distinct nonempty field names.")
        return cls(**values)

    @property
    def endpoint(self):
        if self.data_mode == "suiteql":
            return QUERY_PATH
        return "/services/rest/query/v1/savedsearch/" + quote(self.saved_search_id, safe="") + "/result"


def load_key(config):
    try:
        with open(config.private_key_file, "rb") as handle:
            pem = handle.read(64 * 1024 + 1)
        if len(pem) > 64 * 1024:
            fail("Invalid key: the PEM file is too large.")
        password = config.private_key_password
        key = serialization.load_pem_private_key(
            pem, password=password.encode("utf-8") if password else None,
        )
        if not isinstance(key, rsa.RSAPrivateKey) or key.key_size not in (3072, 4096):
            fail("Invalid key: use a 3072-bit or 4096-bit RSA private key.")
        return key
    except ConnectorError:
        raise
    except Exception:
        fail("Invalid key: check the PEM file, access permissions and passphrase.")


class Budget:
    def __init__(self, clock=time.monotonic, sleeper=time.sleep):
        self.clock = clock
        self.sleeper = sleeper
        self.deadline = clock() + EXECUTION_SECONDS
        self.bytes_read = 0

    def remaining(self):
        value = self.deadline - self.clock()
        if value <= 0:
            fail("Extract incomplete: execution time limit reached. Narrow the source and retry.")
        return value

    def wait(self, seconds):
        if not math.isfinite(seconds) or seconds >= self.remaining():
            fail("Extract incomplete: retry delay exceeds the remaining execution time.")
        self.sleeper(seconds)
        self.remaining()

    def consume(self, size, response_size):
        self.bytes_read += size
        if response_size > PAGE_BYTES or self.bytes_read > TOTAL_BYTES:
            fail("Extract incomplete: response size limit reached. Narrow the source and retry.")
        self.remaining()


def retry_delay(headers, attempt, wall_clock, jitter):
    raw = headers.get("Retry-After", "")
    if isinstance(raw, str):
        try:
            if re.fullmatch(r"\d+", raw.strip()):
                return float(raw)
            moment = parsedate_to_datetime(raw)
            if moment.tzinfo is not None:
                return max(0.0, moment.timestamp() - wall_clock())
        except (ValueError, TypeError, OverflowError):
            pass
    return 2 ** attempt + jitter()


def status_error(stage, status, body):
    code = None
    try:
        payload = decode_json(body)
        if isinstance(payload, dict):
            candidates = [payload.get("error")]
            details = payload.get("o:errorDetails")
            if isinstance(details, list):
                candidates += [item.get("o:errorCode") for item in details if isinstance(item, dict)]
            code = next((item for item in candidates if isinstance(item, str) and item in SAFE_CODES), None)
    except ConnectorError:
        pass
    detail = {
        400: "Authentication rejected. Check the application and certificate mapping." if stage == "Authentication"
        else "Invalid query or search request. Check the source configuration.",
        401: "Authentication rejected. Check the application, certificate mapping and machine clock.",
        403: "Access denied. Ask an administrator to check role permissions and network policy.",
        404: "Source unavailable. Check the ID, role access and account release.",
        429: "Rate limit exhausted. Try again later.",
    }.get(status, "Unexpected HTTP response. Ask an administrator to check the service.")
    suffix = " Code: " + code + "." if code else ""
    return ConnectorError("{}: HTTP {}. {}{}".format(stage, status, detail, suffix))


class Client:
    def __init__(self, config, key, session, budget, progress, wall_clock=time.time, jitter=random.random):
        self.config = config
        self.key = key
        self.session = session
        self.budget = budget
        self.progress = progress
        self.wall_clock = wall_clock
        self.jitter = jitter
        self.token = None
        self.token_deadline = 0

    def assertion(self):
        now = int(self.wall_clock())
        return jwt.encode(
            {"iss": self.config.client_id, "scope": "rest_webservices",
             "aud": self.config.service_url + TOKEN_PATH, "iat": now, "exp": now + 300},
            self.key, algorithm="PS256", headers={"typ": "JWT", "kid": self.config.certificate_id},
        )

    def read_body(self, response):
        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=4096):
            size += len(chunk)
            self.budget.consume(len(chunk), size)
            chunks.append(chunk)
        self.budget.remaining()
        return b"".join(chunks)

    def request(self, method, path, stage, headers, kwargs_factory):
        allowed = {("POST", TOKEN_PATH), (
            "POST" if self.config.data_mode == "suiteql" else "GET", self.config.endpoint,
        )}
        if (method, path) not in allowed:
            fail("Invalid request: endpoint is not permitted.")
        for attempt in range(3):
            remaining = self.budget.remaining()
            response = None
            try:
                response = self.session.request(
                    method, self.config.service_url + path,
                    headers=headers, allow_redirects=False, verify=True, stream=True,
                    timeout=(min(10, remaining), min(120, remaining)), **kwargs_factory(),
                )
                body = self.read_body(response)
                status, response_headers = response.status_code, response.headers
            except requests.exceptions.SSLError:
                fail(stage + ": TLS verification failed. Check the certificate chain and network configuration.")
            except (requests.Timeout, requests.ConnectionError, requests.exceptions.ChunkedEncodingError):
                if attempt == 2:
                    fail(stage + ": network request failed after three attempts.")
                self.budget.wait(2 ** attempt + self.jitter())
                continue
            except requests.RequestException:
                fail(stage + ": network request failed.")
            finally:
                if response is not None:
                    response.close()
            if status not in TRANSIENT or attempt == 2:
                return status, body
            self.budget.wait(retry_delay(response_headers, attempt, self.wall_clock, self.jitter))
        raise AssertionError("unreachable")

    def authenticate(self):
        self.progress("Authenticating")
        started = self.budget.clock()
        status, body = self.request(
            "POST", TOKEN_PATH, "Authentication", {"Accept": "application/json"},
            lambda: {"data": {
                "grant_type": "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion": self.assertion(),
            }},
        )
        if status != 200:
            raise status_error("Authentication", status, body)
        payload = decode_json(body)
        if not isinstance(payload, dict):
            fail("Authentication: unexpected token response.")
        token, kind, expiry = (payload.get(name) for name in ("access_token", "token_type", "expires_in"))
        if (
            not isinstance(token, str) or not token or any(char.isspace() for char in token)
            or not isinstance(kind, str) or kind.lower() != "bearer"
            or type(expiry) is not int or expiry <= RENEW_SECONDS
        ):
            fail("Authentication: unexpected token response.")
        self.token_deadline = started + expiry - RENEW_SECONDS
        if self.token_deadline <= self.budget.clock():
            fail("Authentication: token expired before it could be used.")
        self.token = token

    def page(self, offset, limit):
        # At most two request cycles per page: up to three transient attempts in each.
        for recovery in range(2):
            if self.token is None or self.budget.clock() >= self.token_deadline:
                self.authenticate()
            headers = {"Accept": "application/json", "Authorization": "Bearer " + self.token}
            kwargs = {"params": {"limit": limit, "offset": offset}}
            method = "GET"
            if self.config.data_mode == "suiteql":
                method = "POST"
                headers.update({"Content-Type": "application/json", "Prefer": "transient"})
                kwargs["json"] = {"q": self.config.suiteql}
            status, body = self.request(method, self.config.endpoint, "Data", headers, lambda: kwargs)
            if status == 401 and recovery == 0:
                self.token = None
                continue
            if status != 200:
                raise status_error("Data", status, body)
            return decode_json(body)
        raise AssertionError("unreachable")

    def extract(self):
        sample = self.config.extraction_mode == "sample"
        limit = 100 if sample else 1000
        rows, offset, pages, total = [], 0, 0, None
        while True:
            envelope = self.page(offset, limit)
            if not isinstance(envelope, dict):
                fail("Unexpected response: expected a paging object.")
            items = envelope.get("items")
            count, actual_offset, reported_total = (
                envelope.get(name) for name in ("count", "offset", "totalResults")
            )
            more = envelope.get("hasMore")
            if (
                not isinstance(items, list) or any(not isinstance(row, dict) for row in items)
                or any(type(value) is not int or value < 0 for value in (count, actual_offset, reported_total))
                or type(more) is not bool
            ):
                fail("Unexpected response: invalid or missing paging fields.")
            if (
                count != len(items) or count > limit or actual_offset != offset
                or reported_total < offset + count or more != (offset + count < reported_total)
                or (more and count != limit) or (total is not None and total != reported_total)
            ):
                fail("Extract incomplete: inconsistent paging or changing totals. Retry with a stable source.")
            total = reported_total
            if not sample and (total >= ROW_LIMIT or len(rows) + count >= ROW_LIMIT):
                fail("Extract incomplete: full mode requires fewer than 100,000 rows. Narrow the source.")
            rows.extend(items)
            pages += 1
            self.progress("Retrieved {} pages, {} rows".format(pages, len(rows)))
            self.budget.remaining()
            if sample or not more:
                return rows, pages, more
            offset += limit


def text_value(value):
    if value is None or isinstance(value, str):
        # Omniscope's text output treats empty strings as missing. Make that contract explicit.
        return None if value == "" else value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, use_decimal=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    fail("Unexpected response: unsupported value type.")


def make_frame(rows, configured_columns):
    names = {name for row in rows for name in row if name != "links"}
    if names:
        validate_columns(sorted(names))
    columns = configured_columns if configured_columns is not None else sorted(names)
    if not columns:
        fail("No fields returned: enter comma-separated names in Output fields to define an empty output.")
    # Object arrays contain only strings/None, avoiding pandas' numeric and date inference.
    return pd.DataFrame(
        [[text_value(row.get(name)) for name in columns] for row in rows], columns=columns, dtype=object,
    )


def run(api, session_factory=requests.Session, clock=time.monotonic, sleeper=time.sleep, wall_clock=time.time,
        jitter=random.random):
    stage = "Configuration"
    budget = Budget(clock, sleeper)
    try:
        config = Config.read(api)
        key = load_key(config)
        budget.remaining()
        stage = "Extraction"
        with session_factory() as session:
            # Prevent ambient .netrc credentials replacing Bearer auth. Keep explicitly configured proxies.
            session.trust_env = False
            session.proxies.update(requests.utils.get_environ_proxies(config.service_url))
            client = Client(config, key, session, budget, api.update_message, wall_clock, jitter)
            rows, pages, more = client.extract()
        stage = "Output"
        frame = make_frame(rows, config.output_columns)
        budget.remaining()
        api.write_output(frame, "data")
        budget.remaining()
        label = "Sample" if config.extraction_mode == "sample" else "Complete"
        suffix = "; more rows available" if more else "; no further rows reported"
        api.commit("{}: {} rows, {} pages{}".format(label, len(rows), pages, suffix))
    except ConnectorError as error:
        api.abort(str(error))
    except Exception:
        # Exception strings can contain URLs, queries, tokens, paths or response data.
        api.abort(stage + ": unexpected failure. Check the runtime and dependency setup; no data was committed.")


def main():
    from omniscope.api import OmniscopeApi
    # Socket read timeouts alone do not stop a peer that keeps sending tiny amounts of data.
    # Omniscope discards the transaction on a nonzero process exit, including this hard deadline.
    def expired():
        os.write(2, b"NetSuite: execution time limit reached; extract incomplete.\n")
        os._exit(1)

    watchdog = threading.Timer(EXECUTION_SECONDS, expired)
    watchdog.daemon = True
    watchdog.start()
    try:
        run(OmniscopeApi())
    finally:
        watchdog.cancel()


if __name__ == "__main__":
    main()
