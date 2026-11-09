"""XPT Reader: reads a SAS transport file (XPORT version 5), one dataset to records plus a summary of all of them.

The format is read here directly (it is a fixed layout of 80-byte records and IBM floating-point numbers), so the
block needs nothing beyond pandas and numpy.
"""
import os
import re
import struct

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

LIBRARY_V5 = b"HEADER RECORD*******LIBRARY HEADER RECORD!!!!!!!"
LIBRARY_V8 = b"HEADER RECORD*******LIBV8   HEADER RECORD!!!!!!!"
MEMBER_V5 = b"HEADER RECORD*******MEMBER  HEADER RECORD!!!!!!!"
NAMESTR_V5 = b"HEADER RECORD*******NAMESTR HEADER RECORD!!!!!!!"
OBS_V5 = b"HEADER RECORD*******OBS     HEADER RECORD!!!!!!!"
SAS_EPOCH = pd.Timestamp("1960-01-01")

# SAS formats whose values are days since 1 January 1960, and those that are seconds since then.
DATE_FORMATS = {"DATE", "DAY", "DDMMYY", "DDMMYYB", "DDMMYYC", "DDMMYYD", "DDMMYYN", "DDMMYYP", "DDMMYYS",
                "DOWNAME", "E8601DA", "B8601DA", "JULDAY", "JULIAN", "MMDDYY", "MMDDYYB", "MMDDYYC", "MMDDYYD",
                "MMDDYYN", "MMDDYYP", "MMDDYYS", "MMYY", "MONNAME", "MONTH", "MONYY", "NENGO", "QTR", "QTRR",
                "WEEKDATE", "WEEKDATX", "WEEKDAY", "WORDDATE", "WORDDATX", "YEAR", "YYMM", "YYMMDD", "YYMMDDB",
                "YYMMDDC", "YYMMDDD", "YYMMDDN", "YYMMDDP", "YYMMDDS", "YYMON", "YYQ", "YYQR", "IS8601DA",
                "MINGUO", "EURDFDE", "EURDFDD", "EURDFMY", "EURDFWKX"}
DATETIME_FORMATS = {"DATETIME", "DATEAMPM", "DTDATE", "DTMONYY", "DTWKDATX", "DTYEAR", "DTYYQC", "E8601DT",
                    "B8601DT", "E8601DZ", "B8601DZ", "IS8601DT", "IS8601DZ", "MDYAMPM"}


class XptError(Exception):
    pass


def ibm_to_float(raw, length):
    """IBM System/360 floating point (big-endian, 2 to 8 bytes, right-padded) to IEEE doubles.
    SAS missing values (. .A-.Z ._) are a first byte of '.', 'A'-'Z' or '_' and zeros after it."""
    n = len(raw) // length
    padded = np.zeros((n, 8), dtype=np.uint8)
    padded[:, :length] = np.frombuffer(raw, dtype=np.uint8).reshape(n, length)
    first = padded[:, 0]
    rest_zero = ~padded[:, 1:].any(axis=1)
    missing = rest_zero & ((first == 0x2E) | (first == 0x5F) | ((first >= 0x41) & (first <= 0x5A)))
    words = padded.view(">u8").ravel()
    sign = np.where(words >> 63, -1.0, 1.0)
    exponent = ((words >> 56) & 0x7F).astype(np.int64) - 64
    mantissa = (words & 0x00FFFFFFFFFFFFFF).astype(np.float64) / float(1 << 56)
    values = sign * mantissa * np.power(16.0, exponent)
    values[missing] = np.nan
    return values


def text(raw):
    return raw.decode("latin-1").rstrip(" \x00")


def parse_sas_datetime(raw):
    """Header dates are written like 30JUN25:09:15:00."""
    try:
        return pd.to_datetime(text(raw), format="%d%b%y:%H:%M:%S")
    except (ValueError, TypeError):
        return pd.NaT


def read_xpt(path):
    """Return a list of datasets: dicts with name, label, created, modified, variables and records."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data.startswith(b"**COMPRESSED**"):
        raise XptError("This is a CPORT file (made by PROC CPORT), not a transport file. Ask for the data as an "
                       "XPORT file (the XPORT engine or %LOC2XPT), or open it in SAS with PROC CIMPORT.")
    if data.startswith(LIBRARY_V8):
        raise XptError("This is a version 8 transport file (long names). Only version 5 files are supported; "
                       "ask for the data with the XPORT engine or %LOC2XPT FORMAT=V5.")
    if not data.startswith(LIBRARY_V5):
        raise XptError("This is not a SAS transport file: it does not start with a library header record.")
    if len(data) % 80:
        raise XptError("The file is damaged: its length is not a multiple of 80 bytes.")

    starts = [m.start() for m in re.finditer(re.escape(MEMBER_V5), data) if m.start() % 80 == 0]
    datasets = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(data)
        datasets.append(read_member(data, start, end))
    return datasets


def read_member(data, start, end):
    header = data[start:start + 80]
    namestr_length = int(header[74:78]) if header[74:78].strip() else 140
    pos = start + 160  # member header + descriptor header
    rec1, rec2 = data[pos:pos + 80], data[pos + 80:pos + 160]
    name = text(rec1[8:16])
    created = parse_sas_datetime(rec1[64:80])
    modified = parse_sas_datetime(rec2[0:16])
    label = text(rec2[32:72])
    pos += 160
    if not data[pos:pos + 80].startswith(NAMESTR_V5):
        raise XptError(f"Dataset {name}: variable descriptions not found where expected; the file may be damaged.")
    count = int(data[pos + 54:pos + 58])
    pos += 80
    variables = []
    for k in range(count):
        ns = data[pos + k * namestr_length:pos + (k + 1) * namestr_length].ljust(140, b" ")
        ntype, _, length, _ = struct.unpack(">hhhh", ns[:8])
        fmt_name = text(ns[56:64])
        fmt_width, fmt_decimals = struct.unpack(">hh", ns[64:68])
        position = struct.unpack(">l", ns[84:88])[0]
        variables.append({"name": text(ns[8:16]), "label": text(ns[16:56]), "numeric": ntype == 1,
                          "length": length, "position": position, "format": fmt_name,
                          "format_width": fmt_width, "format_decimals": fmt_decimals})
    pos += count * namestr_length
    if pos % 80:
        pos += 80 - pos % 80
    if not data[pos:pos + 80].startswith(OBS_V5):
        raise XptError(f"Dataset {name}: the records header was not found; the file may be damaged.")
    pos += 80

    record_length = sum(v["length"] for v in variables)
    region = data[pos:end]
    n = len(region) // record_length if record_length else 0
    # The records end with spaces up to the next multiple of 80 bytes. When records are short, that padding can
    # look like whole blank records: drop a blank last record if the data would still fill the same 80-byte cards.
    while n > 0 and len(region) - (n - 1) * record_length < 80 and \
            region[(n - 1) * record_length:n * record_length].strip(b" ") == b"":
        n -= 1
    block = np.frombuffer(region[:n * record_length], dtype=np.uint8).reshape(n, record_length) if n else \
        np.zeros((0, record_length), dtype=np.uint8)

    columns = {}
    for v in variables:
        cells = block[:, v["position"]:v["position"] + v["length"]]
        if v["numeric"]:
            columns[v["name"]] = ibm_to_float(cells.tobytes(), v["length"])
        else:
            values = [text(bytes(row)) for row in cells]
            columns[v["name"]] = pd.Series([s if s != "" else None for s in values], dtype=object)
    records = pd.DataFrame(columns, index=pd.RangeIndex(n))
    return {"name": name, "label": label, "created": created, "modified": modified, "variables": variables,
            "records": records}


def kind_of_format(fmt):
    base = re.sub(r"\d+$", "", fmt.upper().rstrip("."))
    if base in DATE_FORMATS:
        return "date"
    if base in DATETIME_FORMATS:
        return "datetime"
    return None


def convert_dates(records, variables):
    out = records.copy()
    for v in variables:
        kind = kind_of_format(v["format"]) if v["numeric"] else None
        if kind == "date":
            out[v["name"]] = pd.to_datetime(out[v["name"]], unit="D", origin=SAS_EPOCH, errors="coerce")
        elif kind == "datetime":
            out[v["name"]] = pd.to_datetime(out[v["name"]], unit="s", origin=SAS_EPOCH, errors="coerce")
    return out


def format_text(v):
    if not v["format"] and not v["format_width"]:
        return None
    width = str(v["format_width"]) if v["format_width"] else ""
    decimals = str(v["format_decimals"]) if v["format_decimals"] else ""
    return f"{v['format']}{width}.{decimals}"


xpt_file = omniscope_api.get_option("xptFile")
dataset_name = omniscope_api.get_option("datasetName")
dates = omniscope_api.get_option("convertDates")
dates = True if dates is None else bool(dates)

if not xpt_file:
    omniscope_api.abort("Choose the XPT file to read.")
if not os.path.isfile(xpt_file):
    omniscope_api.abort(f"File not found on the server: {xpt_file}")

try:
    datasets = read_xpt(xpt_file)
except XptError as error:
    omniscope_api.abort(str(error))
if not datasets:
    omniscope_api.abort("The file holds no datasets.")

summary = pd.DataFrame({
    "Dataset Name": [d["name"] for d in datasets],
    "Label": [d["label"] or None for d in datasets],
    "Records": pd.array([len(d["records"]) for d in datasets], dtype="Int64"),
    "Field count": pd.array([len(d["variables"]) for d in datasets], dtype="Int64"),
    "Fields": [", ".join(v["name"] for v in d["variables"]) for d in datasets],
    "Created": pd.to_datetime([d["created"] for d in datasets]),
    "Modified": pd.to_datetime([d["modified"] for d in datasets]),
})
variables = pd.DataFrame([
    {"Dataset Name": d["name"], "Position": k + 1, "Field": v["name"], "Label": v["label"] or None,
     "Type": "Number" if v["numeric"] else "Text", "Length": v["length"], "Format": format_text(v),
     "Read as": ("Date" if kind_of_format(v["format"]) and dates and v["numeric"] else
                 "Number" if v["numeric"] else "Text")}
    for d in datasets for k, v in enumerate(d["variables"])
], columns=["Dataset Name", "Position", "Field", "Label", "Type", "Length", "Format", "Read as"])
variables["Position"] = variables["Position"].astype("Int64")
variables["Length"] = variables["Length"].astype("Int64")

if dataset_name and str(dataset_name).strip():
    wanted = str(dataset_name).strip().upper()
    chosen = next((d for d in datasets if d["name"].upper() == wanted), None)
    if chosen is None:
        omniscope_api.abort(f"The file has no dataset called {dataset_name}. Its datasets: "
                            + ", ".join(d["name"] for d in datasets) + ". Leave the option empty to read the first.")
else:
    chosen = datasets[0]

records = convert_dates(chosen["records"], chosen["variables"]) if dates else chosen["records"]

omniscope_api.write_output(summary, "summary")
omniscope_api.write_output(records, "dataset")
omniscope_api.write_output(variables, "variables")
omniscope_api.commit(f"Read dataset {chosen['name']}: {len(records)} records, {len(records.columns)} fields "
                     f"({len(datasets)} dataset(s) in the file).")
