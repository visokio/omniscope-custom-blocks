"""Slack Web API: calls any Slack Web API method (https://api.slack.com/methods) and turns the answer into records,
following the pages of methods that return their results in pages."""
import json
import time

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

API = "https://slack.com/api/"
TIMEOUT = 60
MAX_PAGES = 1000
MAX_RETRIES = 5


def option_text(name):
    value = omniscope_api.get_option(name)
    return "" if value is None else str(value).strip()


def parse_json_option(name, title):
    text = option_text(name)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except ValueError as exc:
        omniscope_api.abort(f"{title} is not valid JSON ({exc.msg} at character {exc.pos + 1}). "
                            'Use double quotes, for example {"channel": "C0123456789"}.')
    if not isinstance(value, dict):
        omniscope_api.abort(f'{title} must be a JSON object, for example {{"channel": "C0123456789"}}.')
    return value


def call(session, method, verb, arguments):
    """One Slack call; waits and retries when Slack says the rate limit was hit."""
    for attempt in range(MAX_RETRIES + 1):
        if verb == "POST":
            response = session.post(API + method, json=arguments, timeout=TIMEOUT)
        else:
            response = session.get(API + method, params=arguments, timeout=TIMEOUT)
        if response.status_code == 429 and attempt < MAX_RETRIES:
            time.sleep(min(float(response.headers.get("Retry-After", "1")), 60))
            continue
        if response.status_code == 404:
            omniscope_api.abort(f"Slack has no method called {method!r}: check the API method name.")
        if not response.ok:
            omniscope_api.abort(f"Slack returned HTTP {response.status_code} for {method}: {response.text[:300]}")
        body = response.json()
        if not body.get("ok", False):
            detail = body.get("error", "unknown error")
            if body.get("needed"):
                detail += f" (the token needs the {body['needed']} scope)"
            omniscope_api.abort(f"Slack refused {method}: {detail}")
        return body
    omniscope_api.abort(f"Slack kept rate-limiting {method}; try again later.")


def records_key(body, wanted):
    """The response key holding the list to turn into records."""
    if wanted:
        if wanted not in body:
            omniscope_api.abort(f"The response has no {wanted!r}; it has: {', '.join(sorted(body))}.")
        return wanted
    for key, value in body.items():
        if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
            return key
    for key, value in body.items():
        if isinstance(value, list) and key not in ("warnings",):
            return key
    return None


def plain(value):
    """Lists and objects left after flattening become JSON text, so every field is text, number or yes/no."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def to_records(items):
    if not items:
        return pd.DataFrame()
    if all(isinstance(v, dict) for v in items):
        df = pd.json_normalize(items)
    else:
        df = pd.DataFrame({"value": items})
    for c in df.columns:
        if df[c].map(lambda v: isinstance(v, (list, dict))).any():
            df[c] = df[c].map(plain)
    return df


token = option_text("authToken")
method = option_text("methodName").strip("/")
verb = option_text("methodType").upper() or "GET"
wanted_key = option_text("recordsFrom")
follow_pages = omniscope_api.get_option("followPages")
follow_pages = True if follow_pages is None else bool(follow_pages)

if not token:
    omniscope_api.abort("Enter a Slack token (from the app's OAuth & Permissions page).")
if not method:
    omniscope_api.abort("Enter an API method name, such as conversations.list.")
if verb == "POST":
    arguments = parse_json_option("jsonPayload", "JSON Payload")
else:
    arguments = parse_json_option("params", "Query Params")

session = requests.Session()
session.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})

pages, items, key = [], [], None
while True:
    body = call(session, method, verb, arguments)
    pages.append(body)
    key = key or records_key(body, wanted_key)
    if key:
        items.extend(body.get(key) or [])
    cursor = (body.get("response_metadata") or {}).get("next_cursor")
    if not (follow_pages and key and cursor) or len(pages) >= MAX_PAGES:
        break
    arguments = dict(arguments, cursor=cursor)
    omniscope_api.update_message(f"Slack: {len(items):,} records from {len(pages)} pages")

if key:
    records = to_records(items)
    if records.empty and not len(records.columns):
        records = pd.DataFrame({key: pd.Series([], dtype=object)})
else:
    # No list in the answer (users.profile.get, chat.postMessage...): the answer itself is the one record
    records = to_records([{k: v for k, v in pages[0].items() if k != "ok"}])

raw = pd.DataFrame({"Text Response": [json.dumps(p, ensure_ascii=False) for p in pages]})

omniscope_api.write_output_records(records, output_number=0)
omniscope_api.write_output_records(raw, output_number=1)
where = f" from {key!r}" if key else ""
omniscope_api.close(f"{len(records):,} records{where}, {len(pages)} page{'s' if len(pages) > 1 else ''}.")
