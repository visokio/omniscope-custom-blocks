"""Overpass Street Coordinates: for each street name in a field, finds the OpenStreetMap streets with that
name (optionally inside a bounding box) through the Overpass API, and writes one record per point along each."""
import re
import time

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"
# The public Overpass servers refuse requests without a descriptive User-Agent (HTTP 406)
USER_AGENT = "Omniscope-Overpass-Street-Coordinates/2.0 (+https://github.com/visokio/omniscope-custom-blocks)"
QUERY_TIMEOUT = 120       # seconds the server may spend on one query
RETRY_WAIT = 30           # the usage policy asks for a pause after 429 (too many requests) or 504 (busy)
RETRIES = 3
NUMBER = r"-?\d+(?:\.\d+)?"


def option_text(name):
    value = omniscope_api.get_option(name)
    return "" if value is None else str(value).strip()


def ql_string(text):
    """Text as an Overpass QL string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def parse_bbox(text):
    """'south, west, north, east' in decimal degrees -> the QL bounding-box filter, or '' when empty."""
    if not text:
        return ""
    parts = [p.strip() for p in text.replace(";", ",").split(",")]
    if len(parts) != 4 or not all(re.fullmatch(NUMBER, p) for p in parts):
        omniscope_api.abort(f"Bounding box must be four numbers 'south, west, north, east'; got '{text}'.")
    s, w, n, e = (float(p) for p in parts)
    if not (-90 <= s < n <= 90 and -180 <= w <= 180 and -180 <= e <= 180 and w != e):
        omniscope_api.abort(f"Bounding box '{text}' is not south, west, north, east in degrees "
                            "(south must be below north).")
    return f"({s},{w},{n},{e})"


def regex_literal(text):
    """Text as a regular expression that matches it literally (POSIX extended syntax, as Overpass uses)."""
    return re.sub(r"([.\[\]()*+?{}|^$\\])", r"\\\1", text)


def build_query(street, match, bbox):
    if match == "contains":
        name_filter = f'["name"~{ql_string(regex_literal(street))},i]'
    else:
        name_filter = f'["name"={ql_string(street)}]'
    return f"[out:json][timeout:{QUERY_TIMEOUT}];way[\"highway\"]{name_filter}{bbox};out geom;"


class OverpassError(Exception):
    pass


def run_query(session, endpoint, query):
    for attempt in range(RETRIES + 1):
        try:
            r = session.request("POST", endpoint, data={"data": query}, timeout=QUERY_TIMEOUT + 60)
        except requests.RequestException as e:
            raise OverpassError(f"Could not reach the Overpass API at {endpoint}: {type(e).__name__}")
        if r.status_code in (429, 504) and attempt < RETRIES:
            omniscope_api.update_message(f"Overpass server busy (HTTP {r.status_code}); waiting {RETRY_WAIT} s")
            time.sleep(RETRY_WAIT)
            continue
        if r.status_code == 400:
            raise OverpassError("The Overpass API rejected the query (HTTP 400).")
        if r.status_code != 200:
            raise OverpassError(f"The Overpass API answered HTTP {r.status_code}"
                                + (" (too many requests; try again later)." if r.status_code == 429 else "."))
        try:
            body = r.json()
        except ValueError:
            raise OverpassError("The Overpass API's answer was not JSON.")
        remark = str(body.get("remark") or "")
        if "runtime error" in remark.lower():  # e.g. the query timed out on the server
            raise OverpassError(f"The Overpass API could not finish the query: {remark.strip()}")
        return body.get("elements") or []
    raise OverpassError("The Overpass API was still busy after several attempts.")


street_field = omniscope_api.get_option("addressField")
match = option_text("matchMode") or "exact"
bbox = parse_bbox(option_text("bbox"))
endpoint = option_text("endpoint") or DEFAULT_ENDPOINT

input_data = omniscope_api.read_input_records(input_number=0)
if input_data is None:
    omniscope_api.abort("Connect a block with a field of street names to the input.")
if not street_field or street_field not in input_data.columns:
    omniscope_api.abort("Choose the field that holds the street names in 'Street name field'.")
if not re.match(r"^https?://", endpoint, re.I):
    omniscope_api.abort(f"Overpass API address must start with http:// or https://; got '{endpoint}'.")

OUT_FIELDS = ["Street name", "Way ID", "Point", "Node ID", "Latitude", "Longitude"]
# The input value comes first, under the input field's name (with " (input)" added if that name is taken)
key_field = street_field if street_field not in OUT_FIELDS else f"{street_field} (input)"
COLUMNS = [key_field] + OUT_FIELDS

# Distinct street names in input order; missing and empty values are skipped
streets = []
for value in input_data[street_field].tolist():
    if value is None or value is pd.NA or (isinstance(value, float) and pd.isna(value)):
        continue
    text = str(value).strip()
    if text and text not in streets:
        streets.append(text)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})
rows, not_found = [], []
try:
    for n, street in enumerate(streets, 1):
        omniscope_api.update_message(f"Street {n} of {len(streets)}: {street}")
        found = False
        for el in run_query(session, endpoint, build_query(street, match, bbox)):
            if el.get("type") != "way":
                continue
            nodes = el.get("nodes") or []
            for i, point in enumerate(el.get("geometry") or []):
                if not point:  # a point outside a bounding box can come back empty
                    continue
                found = True
                rows.append([street, (el.get("tags") or {}).get("name"), el.get("id"), i + 1,
                             nodes[i] if i < len(nodes) else None, point.get("lat"), point.get("lon")])
        if not found:
            not_found.append(street)
except OverpassError as e:
    omniscope_api.abort(str(e))

output = pd.DataFrame(rows, columns=COLUMNS)
output[key_field] = output[key_field].astype(object)
output["Street name"] = output["Street name"].astype(object)
for c in ("Way ID", "Point", "Node ID"):
    output[c] = pd.to_numeric(output[c]).astype("Int64")
for c in ("Latitude", "Longitude"):
    output[c] = pd.to_numeric(output[c]).astype("float64")
omniscope_api.write_output_records(output, output_number=0)

message = f"{len(output)} points on {output['Way ID'].nunique()} ways for {len(streets) - len(not_found)} " \
          f"of {len(streets)} street name(s)."
if not_found:
    message += f" No street found for {len(not_found)}, such as '{not_found[0]}'."
omniscope_api.close(message)
