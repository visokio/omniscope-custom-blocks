"""Data Validation Rules: check data against a list of rules and report every
violation, a summary per rule, and a pass / fail flag per row.

Rules come from a table on input 2 (Field, Check, Value, Severity, optional
Rule Name) or are typed in the options, one per line:  Field | CHECK | value | severity

Checks:
  NOT_EMPTY            value present (blank text counts as empty)
  UNIQUE               no duplicates in the field (empty values ignored)
  MIN / MAX            numeric (or date) at least / at most the value
  BETWEEN              numeric (or date) within "low..high"
  ALLOWED / NOT_ALLOWED  value in / not in a list "a|b|c" (case-insensitive)
  PATTERN              text matches a regular expression (whole value)
  MIN_LENGTH / MAX_LENGTH  text length
  IS_NUMBER / IS_DATE  value can be read as a number / date
  NOT_FUTURE           date not after today (or after the value, if given)
  EMAIL                looks like an email address
  UK_POSTCODE          looks like a UK postcode
  COMPARE              compare with another field, for example "<= Credit Limit" or "> Start Date"
  REQUIRED_IF          not empty when another field has a value, for example "Country = UK"

Empty values pass every check except NOT_EMPTY and REQUIRED_IF, so emptiness
is reported once, by the rule meant for it. Values that cannot be read as a
number or date fail range checks (MIN, MAX, BETWEEN, NOT_FUTURE), so text in a
numeric field is never passed silently.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


rules_txt = opt("rules", "")
key_fields = list(opt("key_fields", []) or [])
r_field, r_check, r_value, r_sev, r_name = (opt("rule_field_field"), opt("rule_check_field"), opt("rule_value_field"),
                                            opt("rule_severity_field"), opt("rule_name_field"))
max_examples = int(opt("examples", 3))

df = omniscope_api.read_input_records(input_number=0)
rt = omniscope_api.read_input_records(input_number=1)
if df is None:
    omniscope_api.abort("Connect the data to check to input 1.")
miss = [k for k in key_fields if k not in df.columns]
if miss:
    omniscope_api.abort(f"Key fields not in the input: {', '.join(miss)}")
CHECKS = {"NOT_EMPTY", "UNIQUE", "MIN", "MAX", "BETWEEN", "ALLOWED", "NOT_ALLOWED", "PATTERN", "MIN_LENGTH", "MAX_LENGTH", "IS_NUMBER", "IS_DATE",
          "NOT_FUTURE", "EMAIL", "UK_POSTCODE", "COMPARE", "REQUIRED_IF"}


def cell(v):
    if v is None or (isinstance(v, float) and v != v):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


rules = []
if rt is not None:
    for f, lab in ((r_field, "field"), (r_check, "check")):
        if not f or f not in rt.columns:
            omniscope_api.abort(f"Choose the {lab} column of the rules table (input 2).")
    for f in (r_value, r_sev, r_name):
        if f and f not in rt.columns:
            omniscope_api.abort(f"Column '{f}' is not in the rules table.")
    for i, r in rt.reset_index(drop=True).iterrows():
        rules.append({"field": cell(r[r_field]), "check": cell(r[r_check]).upper().replace(" ", "_"), "value": cell(r[r_value]) if r_value else "",
                      "severity": (cell(r[r_sev]) if r_sev else "") or "Error", "name": (cell(r[r_name]) if r_name else "") or None, "line": i + 1})
for i, line in enumerate((rules_txt or "").splitlines()):
    if not line.strip() or line.strip().startswith("#"):
        continue
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 2:
        omniscope_api.abort(f"Rule line {i + 1} needs at least 'Field | CHECK': {line}")
    sev = ""
    rest = parts[2:]
    if len(rest) >= 2 and rest[-1].lower() in ("error", "warning", "warn", ""):
        sev = rest[-1]
        rest = rest[:-1]
    # list values such as A|B|C contain the separator: join the remaining parts back together
    rules.append({"field": parts[0], "check": parts[1].upper().replace(" ", "_"), "value": "|".join(rest).strip(),
                  "severity": sev or "Error", "name": None, "line": i + 1})
if not rules:
    omniscope_api.abort("Give at least one rule: connect a rules table to input 2, or type rules in the options.")
for r in rules:
    if r["field"] not in df.columns:
        omniscope_api.abort(f"Rule {r['line']}: field '{r['field']}' is not in the data.")
    if r["check"] not in CHECKS:
        omniscope_api.abort(f"Rule {r['line']}: unknown check '{r['check']}'. Use one of: {', '.join(sorted(CHECKS))}.")
    sev = r["severity"].strip().lower()
    r["severity"] = "Warning" if sev.startswith("warn") else "Error"
    r["name"] = r["name"] or f"{r['field']} {r['check'].replace('_', ' ').lower()}" + (f" {r['value']}" if r["value"] else "")


def to_num(s):
    return pd.to_numeric(s, errors="coerce").astype("float64")


def to_date(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s
        if getattr(d.dt, "tz", None) is not None:
            d = d.dt.tz_localize(None)
        return d.astype("datetime64[ns]")
    txt = s.astype(object).map(cell)
    iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
    d = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    d[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
    rest = ~iso & (txt != "")
    d[rest] = pd.to_datetime(txt[rest], errors="coerce", dayfirst=True, format="mixed")
    return d


def scalar_date(v):
    return to_date(pd.Series([v], dtype=object)).iloc[0]


def bound(series, v):
    """Compare numerically when the field is numeric, otherwise as dates."""
    if pd.api.types.is_datetime64_any_dtype(series) or (not pd.api.types.is_numeric_dtype(series) and to_num(series).notna().sum() == 0):
        return to_date(series), scalar_date(v)
    return to_num(series), float(v)


EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
POSTCODE = re.compile(r"^(GIR ?0AA|[A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2})$", re.I)
OPS = {"<=": np.less_equal, "<": np.less, ">=": np.greater_equal, ">": np.greater, "=": np.equal, "==": np.equal, "!=": np.not_equal, "<>": np.not_equal}

n = len(df)
txt_cache = {}
fails = []   # (rule index, row positions array, found values)
for ri, r in enumerate(rules):
    s = df[r["field"]]
    if r["field"] not in txt_cache:
        txt_cache[r["field"]] = s.astype(object).map(cell)
    t = txt_cache[r["field"]]
    empty = (t == "").to_numpy()
    c, v = r["check"], r["value"]
    try:
        if c == "NOT_EMPTY":
            bad = empty
        elif c == "UNIQUE":
            key = t.str.lower() if not pd.api.types.is_numeric_dtype(s) else t
            bad = key.duplicated(keep=False).to_numpy() & ~empty
        elif c in ("MIN", "MAX", "BETWEEN"):
            if c == "BETWEEN":
                lo_v, hi_v = [x.strip() for x in v.split("..")]
                vals, lo = bound(s, lo_v)
                _, hi = bound(s, hi_v)
                ok = (vals >= lo) & (vals <= hi)
            else:
                vals, b = bound(s, v)
                ok = vals >= b if c == "MIN" else vals <= b
            bad = ~ok.to_numpy() & ~empty  # unreadable values fail (they are not empty)
        elif c in ("ALLOWED", "NOT_ALLOWED"):
            allowed = {x.strip().lower() for x in v.split("|")}
            inside = t.str.lower().isin(allowed).to_numpy()
            bad = (~inside if c == "ALLOWED" else inside) & ~empty
        elif c == "PATTERN":
            rx = re.compile(v)
            bad = ~t.map(lambda x: bool(rx.fullmatch(x))).to_numpy() & ~empty
        elif c in ("MIN_LENGTH", "MAX_LENGTH"):
            ln = t.str.len().to_numpy()
            bad = ((ln < int(v)) if c == "MIN_LENGTH" else (ln > int(v))) & ~empty
        elif c == "IS_NUMBER":
            bad = to_num(t.str.replace(",", "", regex=False)).isna().to_numpy() & ~empty
        elif c == "IS_DATE":
            bad = to_date(s).isna().to_numpy() & ~empty
        elif c == "NOT_FUTURE":
            lim = scalar_date(v) if v else pd.Timestamp.today().normalize() + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
            d = to_date(s)
            bad = ((d > lim) | d.isna()).to_numpy() & ~empty
        elif c == "EMAIL":
            bad = ~t.map(lambda x: bool(EMAIL.match(x))).to_numpy() & ~empty
        elif c == "UK_POSTCODE":
            bad = ~t.map(lambda x: bool(POSTCODE.match(x))).to_numpy() & ~empty
        elif c == "COMPARE":
            m = re.match(r"^\s*(<=|>=|==|!=|<>|<|>|=)\s*(.+?)\s*$", v)
            if not m or m.group(2) not in df.columns:
                omniscope_api.abort(f"Rule {r['line']}: COMPARE needs an operator and another field, for example '<= Credit Limit'.")
            other = df[m.group(2)]
            a_, b_ = (to_date(s), to_date(other)) if (pd.api.types.is_datetime64_any_dtype(s) or to_num(s).notna().sum() == 0) else (to_num(s), to_num(other))
            both = a_.notna() & b_.notna()
            res = OPS[m.group(1)](a_.to_numpy(), b_.to_numpy())
            bad = both.to_numpy() & ~res
        elif c == "REQUIRED_IF":
            m = re.match(r"^\s*(.+?)\s*(=|!=)\s*(.*?)\s*$", v)
            if not m or m.group(1) not in df.columns:
                omniscope_api.abort(f"Rule {r['line']}: REQUIRED_IF needs a condition on another field, for example 'Country = UK'.")
            ot = df[m.group(1)].astype(object).map(cell).str.lower()
            cond = (ot == m.group(3).lower()) if m.group(2) == "=" else (ot != m.group(3).lower())
            bad = cond.to_numpy() & empty
    except (ValueError, re.error) as e:
        omniscope_api.abort(f"Rule {r['line']} ({r['name']}): could not use the value '{v}': {e}")
    idx = np.nonzero(bad)[0]
    fails.append((ri, idx, t.iloc[idx].to_numpy(dtype=object)))

# violations
vrows = []
for ri, idx, found in fails:
    r = rules[ri]
    for i, fv in zip(idx, found):
        vrows.append((i, ri, fv))
vio = pd.DataFrame(vrows, columns=["row", "ri", "Value Found"])
vio = vio.sort_values(["row", "ri"], kind="mergesort").reset_index(drop=True)
out_v = pd.DataFrame({"Row Number": (vio["row"] + 1).astype("int64")})
for k in key_fields:
    out_v[k] = df[k].iloc[vio["row"].to_numpy()].to_numpy(dtype=object) if len(vio) else pd.Series([], dtype=object)
out_v["Rule"] = [rules[i]["name"] for i in vio["ri"]]
out_v["Field"] = [rules[i]["field"] for i in vio["ri"]]
out_v["Check"] = [rules[i]["check"] for i in vio["ri"]]
out_v["Rule Value"] = [rules[i]["value"] or None for i in vio["ri"]]
out_v["Severity"] = [rules[i]["severity"] for i in vio["ri"]]
out_v["Value Found"] = vio["Value Found"].replace("", None).astype(object).to_numpy()

# per rule
srows = []
for ri, idx, found in fails:
    r = rules[ri]
    ex = list(dict.fromkeys([f if f != "" else "(empty)" for f in found]))[:max_examples]
    srows.append({"Rule": r["name"], "Field": r["field"], "Check": r["check"], "Rule Value": r["value"] or None, "Severity": r["severity"],
                  "Rows Checked": n, "Rows Failing": len(idx), "Failure Rate": len(idx) / n if n else 0.0,
                  "Status": "Pass" if len(idx) == 0 else ("Fail" if r["severity"] == "Error" else "Warning"),
                  "Example Values": "; ".join(ex) if ex else None, "First Failing Row": int(idx[0]) + 1 if len(idx) else None})
summ = pd.DataFrame(srows)
summ["Rows Checked"] = summ["Rows Checked"].astype("int64")
summ["Rows Failing"] = summ["Rows Failing"].astype("int64")
summ["Failure Rate"] = summ["Failure Rate"].astype("float64")
summ["First Failing Row"] = pd.array(pd.to_numeric(summ["First Failing Row"]).to_numpy(dtype=float), dtype="Float64").astype("Int64")

# per row
err = np.zeros(n, dtype=int)
warn = np.zeros(n, dtype=int)
names_per_row = [[] for _ in range(n)]
for ri, idx, _ in fails:
    r = rules[ri]
    if r["severity"] == "Error":
        err[idx] += 1
    else:
        warn[idx] += 1
    for i in idx:
        names_per_row[i].append(r["name"])
rows = df.copy()
rows["Errors"] = err.astype("int64")
rows["Warnings"] = warn.astype("int64")
rows["Failed Rules"] = ["; ".join(x) if x else None for x in names_per_row]
rows["Valid"] = np.where(err == 0, "Yes", "No")

omniscope_api.write_output(out_v, "violations")
omniscope_api.write_output(summ, "rules")
omniscope_api.write_output(rows, "rows")
n_fail_rules = int((summ["Status"] == "Fail").sum())
omniscope_api.close(f"{len(rules)} rules on {n:,} rows: {int((err > 0).sum()):,} rows with errors, {int(((warn > 0) & (err == 0)).sum()):,} with warnings only; "
                    f"{n_fail_rules} rule(s) failed, {int((summ['Status'] == 'Warning').sum())} warned, {int((summ['Status'] == 'Pass').sum())} passed.")
