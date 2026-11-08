"""Data Cleansing: the common clean-up steps in one block, as a single
checklist, plus a report of what changed.

- remove empty rows / empty fields
- treat placeholder text (NULL, N/A, -) as missing
- replace missing text with blank and missing numbers with 0
- trim, collapse or remove whitespace; remove letters, digits, punctuation,
  invisible / non-printable characters
- change case (UPPER, lower, Title)
"""
import re

import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None else v


fields = opt("fields") or []
remove_null_rows = opt("remove_null_rows", True)
remove_null_columns = opt("remove_null_columns", False)
null_tokens_text = opt("null_tokens", "")
replace_null_text = opt("replace_null_text", True)
replace_null_numbers = opt("replace_null_numbers", True)
trim = opt("trim", True)
collapse_ws = opt("collapse_whitespace", False)
remove_all_ws = opt("remove_all_whitespace", False)
remove_letters = opt("remove_letters", False)
remove_numbers = opt("remove_numbers", False)
remove_punct = opt("remove_punctuation", False)
remove_invisible = opt("remove_invisible", False)
case = opt("modify_case", "NONE")
convert_numbers = opt("convert_numbers", False)
case_fields = opt("case_fields") or []

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to cleanse to the input.")

missing = [f for f in list(fields) + list(case_fields) if f not in df.columns]
if missing:
    omniscope_api.abort(f"Fields not in the input: {', '.join(missing)}")
targets = list(fields) if fields else list(df.columns)

null_tokens = {t.strip() for t in re.split(r"[,;\n]", null_tokens_text or "") if t.strip()}
null_tokens_lower = {t.lower() for t in null_tokens}


def is_text(s):
    return (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)) and not pd.api.types.is_datetime64_any_dtype(s)


def is_number(s):
    return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


INVISIBLE = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f​-‏  ⁠﻿]")
NBSP = re.compile(r"[  -   　]")
PUNCT = re.compile(r"[^\w\s]|_")


def _title_word(w):
    # keep deliberate mixed case (MacLeod, McDonald, iPhone); fix ALL CAPS and all lower
    letters = [c for c in w if c.isalpha()]
    if letters and not (all(c.isupper() for c in letters) or all(c.islower() for c in letters)):
        return w
    w = w.lower()
    w = re.sub(r"(^|[\-/(])(\w)", lambda m: m.group(1) + m.group(2).upper(), w)
    # O'Brien, D'Arcy: capitalise after an apostrophe that follows a single letter
    w = re.sub(r"^(\w)['\u2019](\w)", lambda m: m.group(1).upper() + "'" + m.group(2).upper(), w)
    w = re.sub(r"^Mc(\w)", lambda m: "Mc" + m.group(1).upper(), w)
    return w


def title_case(s):
    return re.sub(r"\S+", lambda m: _title_word(m.group(0)), s)


NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")


def to_number(s):
    """Convert a cleaned text column to numbers when every non-empty value is
    numeric (currency symbols and thousands separators allowed). Values with a
    leading zero (codes, phone numbers) keep the field as text."""
    vals = s.dropna().astype(str).str.strip()
    vals = vals[vals != ""]
    if vals.empty:
        return None
    raw = vals.str.replace(r"^([+-]?)[£$€]", r"\1", regex=True).str.replace(r"(?<=\d),(?=\d{3}\b)", "", regex=True)
    if not raw.str.match(NUMBER).all():
        return None
    if raw.str.match(r"^[+-]?0\d").any():
        return None
    nums = pd.to_numeric(raw)
    res = pd.Series([None] * len(s), index=s.index, dtype="float64")
    res.loc[nums.index] = nums.astype(float).values
    if (nums == nums.round()).all() and (nums.abs() < 2 ** 53).all() and not raw.str.contains(r"\.").any():
        return res.astype("Int64")
    return res


def _txt(v):
    """Comparable text form, so 4 (number) and "4" (text) count as unchanged."""
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


converted = []
report = []
n_rows_in = len(df)
out = df.copy()

for col in targets:
    s = out[col]
    before = s.copy()
    nulls_replaced = 0
    tokens_nulled = 0
    if is_text(s):
        mask = s.notna()
        vals = s[mask].astype(str)
        if null_tokens:
            tok = vals.str.strip().str.lower().isin(null_tokens_lower)
            tokens_nulled = int(tok.sum())
            vals = vals[~tok]
            mask.loc[tok[tok].index] = False
        if remove_invisible:
            vals = vals.str.replace(NBSP, " ", regex=True).str.replace(INVISIBLE, "", regex=True)
        if remove_all_ws:
            vals = vals.str.replace(r"\s+", "", regex=True)
        elif collapse_ws:
            vals = vals.str.replace(r"\s+", " ", regex=True)
        if remove_letters:
            vals = vals.str.replace(r"[^\W\d_]", "", regex=True)
        if remove_numbers:
            vals = vals.str.replace(r"\d", "", regex=True)
        if remove_punct:
            vals = vals.str.replace(PUNCT, "", regex=True)
        if trim:
            vals = vals.str.strip()
        if not case_fields or col in case_fields:
            if case == "UPPER":
                vals = vals.str.upper()
            elif case == "LOWER":
                vals = vals.str.lower()
            elif case == "TITLE":
                vals = vals.map(title_case)
        new = pd.Series([None] * len(s), index=s.index, dtype=object)
        new.loc[vals.index] = vals.values
        num = to_number(new) if convert_numbers else None
        if num is not None:
            converted.append(str(col))
            nulls_replaced = int(num.isna().sum()) if replace_null_numbers else 0
            out[col] = num.fillna(0) if replace_null_numbers else num
            kind = "Text to number"
        elif replace_null_text:
            nulls_replaced = int(new.isna().sum())
            new = new.where(new.notna(), "")
        if num is None:
            out[col] = new
            kind = "Text"
    elif is_number(s):
        if replace_null_numbers:
            nulls_replaced = int(s.isna().sum())
            out[col] = s.fillna(0)
        kind = "Number"
    else:
        kind = "Date" if pd.api.types.is_datetime64_any_dtype(s) else "Other"
    a = before.astype(object).where(before.notna(), None).tolist()
    b = out[col].astype(object).where(out[col].notna(), None).tolist()
    changed = int(sum(1 for x, y in zip(a, b) if _txt(x) != _txt(y)))
    report.append({"Field": str(col), "Type": kind, "Values Changed": changed,
                   "Placeholders Set To Missing": tokens_nulled, "Missing Values Filled": nulls_replaced})


def empty(s):
    if is_text(s):
        return s.isna() | (s.astype(str).str.strip() == "")
    return s.isna()


rows_removed = 0
if remove_null_rows and len(out):
    # a row is empty when every field is empty (judged on the original values,
    # placeholders counting as empty, so that filling blanks / 0 does not hide it)
    orig = df.copy()
    for c in targets:
        if is_text(orig[c]) and null_tokens:
            orig[c] = orig[c].where(~orig[c].astype(str).str.strip().str.lower().isin(null_tokens_lower))
    all_empty = pd.concat([empty(orig[c]) for c in orig.columns], axis=1).all(axis=1)
    rows_removed = int(all_empty.sum())
    out = out[~all_empty.values].reset_index(drop=True)

cols_removed = []
if remove_null_columns:
    for c in targets:
        if len(df) and empty(df[c]).all():
            cols_removed.append(c)
    out = out.drop(columns=cols_removed)

rep = pd.DataFrame(report, columns=["Field", "Type", "Values Changed", "Placeholders Set To Missing", "Missing Values Filled"])
rep["Field Removed"] = ["Yes" if f in cols_removed else "No" for f in rep["Field"]]
rep["Converted To Number"] = ["Yes" if f in converted else "No" for f in rep["Field"]]
for c in ("Values Changed", "Placeholders Set To Missing", "Missing Values Filled"):
    rep[c] = rep[c].astype("int64")
rep.loc[len(rep)] = {"Field": "(empty rows removed)", "Type": "", "Values Changed": rows_removed,
                     "Placeholders Set To Missing": 0, "Missing Values Filled": 0, "Field Removed": "",
                     "Converted To Number": ""}

omniscope_api.write_output(out, "cleansed")
omniscope_api.write_output(rep, "report")
total = int(rep["Values Changed"].iloc[:-1].sum())
omniscope_api.close(f"{n_rows_in:,} rows in, {len(out):,} out; {total:,} values changed; "
                    f"{rows_removed:,} empty rows and {len(cols_removed)} empty fields removed.")
