"""Writes sample-data/trial-sample.xpt, an invented SAS transport file (XPORT version 5) with two datasets.

Everything in it is invented: a fictional study DEMO-01 with 24 subjects (ADSL) and their blood pressure at three
visits (VS). The writer below follows the published XPORT version 5 layout; it needs only pandas and numpy.

    python3 sample-data/make_sample_xpt.py
"""
import math
import os
import random
import re
import struct

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SAS_EPOCH = pd.Timestamp("1960-01-01")
STAMP = b"30JUN25:09:15:00"


def ibm(value):
    """An IEEE double as an 8-byte IBM System/360 float; missing as SAS '.'."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return b"." + b"\x00" * 7
    if value == 0:
        return b"\x00" * 8
    sign = 0x80 if value < 0 else 0
    x = abs(value)
    exponent = math.floor(math.log(x, 16)) + 1
    mantissa = round(x / 16.0 ** exponent * (1 << 56))
    if mantissa >= 1 << 56:
        exponent += 1
        mantissa = round(x / 16.0 ** exponent * (1 << 56))
    return bytes([sign | (exponent + 64)]) + mantissa.to_bytes(7, "big")


def card(text):
    return text.ljust(80)[:80].encode("latin-1")


def header(kind, tail="000000000000000000000000000000  "):
    return card(f"HEADER RECORD*******{kind:<8}HEADER RECORD!!!!!!!{tail}")


def member(name, label, df, labels, formats):
    out = [header("MEMBER", "000000000000000001600000000140  "), header("DSCRPTR"),
           card(f"SAS     {name:<8}SASDATA 9.4     Linux   " + " " * 24) [:64] + STAMP,
           STAMP + b" " * 16 + label.ljust(40).encode("latin-1") + b" " * 8,
           header("NAMESTR", f"000000{len(df.columns):04d}00000000000000000000  ")]
    names, lengths, position = b"", [], 0
    for k, col in enumerate(df.columns):
        numeric = pd.api.types.is_float_dtype(df[col])
        length = 8 if numeric else max([1] + [len(v) for v in df[col].dropna()])
        fmt_name, width, decimals = re.fullmatch(r"((?:[A-Z$][A-Z0-9]*?)?)(\d*)\.(\d*)", formats.get(col) or ".").groups()
        names += struct.pack(">hhhh8s40s8shhh2s8shhl52s", 1 if numeric else 2, 0, length, k + 1,
                             col.ljust(8).encode(), labels[col].ljust(40).encode("latin-1"),
                             fmt_name.ljust(8).encode(), int(width or 0), int(decimals or 0), 0, b"\x00\x00", b" " * 8, 0, 0,
                             position, b"\x00" * 52)
        lengths.append((col, numeric, length))
        position += length
    names += b" " * (-len(names) % 80)
    out.append(names)
    out.append(header("OBS"))
    rows = b""
    for _, r in df.iterrows():
        for col, numeric, length in lengths:
            rows += ibm(r[col]) if numeric else ("" if pd.isna(r[col]) else r[col]).ljust(length).encode("latin-1")
    rows += b" " * (-len(rows) % 80)
    out.append(rows)
    return b"".join(out)


def write_xpt(path, members):
    lib = [header("LIBRARY"), card("SAS     SAS     SASLIB  9.4     Linux   " + " " * 24)[:64] + STAMP,
           STAMP + b" " * 64]
    with open(path, "wb") as fh:
        fh.write(b"".join(lib + [member(*m) for m in members]))


rng = random.Random(7)
arms = ["Placebo", "Low dose", "High dose"]
sites = ["Leeds", "Bristol", "Glasgow", "Cardiff"]
rows = []
for i in range(24):
    start = pd.Timestamp("2025-02-03") + pd.Timedelta(days=3 * i + rng.randint(0, 2))
    rows.append({"STUDYID": "DEMO-01", "USUBJID": f"DEMO-01-{101 + i:03d}", "SITE": sites[i % 4],
                 "SEX": "F" if i % 2 == 0 else "M", "AGE": float(rng.randint(24, 78)), "ARM": arms[i % 3],
                 "TRTSDT": float((start - SAS_EPOCH).days), "WEIGHTBL": round(rng.uniform(52, 104), 1),
                 "SAFFL": "Y"})
adsl = pd.DataFrame(rows)
adsl.loc[[5, 17], "WEIGHTBL"] = float("nan")  # baseline weight not recorded
adsl.loc[23, "TRTSDT"] = float("nan")  # randomised, never treated
adsl.loc[23, "SAFFL"] = "N"

vs = []
for r in rows[:23]:
    for visit, week in (("Baseline", 0), ("Week 4", 4), ("Week 8", 8)):
        for test, unit, base in (("SYSBP", "mmHg", 128), ("DIABP", "mmHg", 82)):
            value = float(base + rng.randint(-14, 14) - (week if r["ARM"] != "Placebo" else 0))
            vs.append({"USUBJID": r["USUBJID"], "VISIT": visit, "VSTESTCD": test, "VSSTRESN": value,
                       "VSSTRESU": unit, "VSDT": r["TRTSDT"] + 7 * week})
vs = pd.DataFrame(vs)
vs.loc[[10, 11], "VSSTRESN"] = float("nan")  # a missed reading

labels = {
    "STUDYID": "Study identifier", "USUBJID": "Unique subject identifier", "SITE": "Study site",
    "SEX": "Sex", "AGE": "Age (years)", "ARM": "Planned treatment arm", "TRTSDT": "Date of first dose",
    "WEIGHTBL": "Baseline weight (kg)", "SAFFL": "Safety population flag", "VISIT": "Visit name",
    "VSTESTCD": "Vital signs test code", "VSSTRESN": "Result (numeric)", "VSSTRESU": "Result unit",
    "VSDT": "Date of measurement",
}
formats = {"TRTSDT": "DATE9.", "VSDT": "YYMMDD10.", "WEIGHTBL": "8.1"}

if __name__ == "__main__":
    write_xpt(os.path.join(HERE, "trial-sample.xpt"),
              [("ADSL", "Subject-level analysis data", adsl, labels, formats),
               ("VS", "Vital signs", vs, labels, formats)])
    print(len(adsl), "ADSL records,", len(vs), "VS records")
