"""RegEx Parse: apply a regular expression to a text field, with four
modes:

  PARSE     capture groups become new fields (named groups name the fields)
  REPLACE   replace every match, with back-references such as \\1 or $1
  TOKENISE  every match becomes a new column (up to N) or a new row
  MATCH     a Yes / No field saying whether the text matches

Python regular expression syntax. Vectorised with pandas string methods.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


field = opt("field")
mode = opt("mode", "PARSE")
pattern = opt("pattern")
ignore_case = opt("ignore_case", True)
replacement = omniscope_api.get_option("replacement") or ""
names = opt("output_names", "")
tokenise_to = opt("tokenise_to", "COLUMNS")
max_cols = int(opt("max_columns", 5))
match_type = opt("match_type", "CONTAINS")
out_name = opt("output_field", "")
keep_unmatched = opt("keep_unmatched", True)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
if not field or field not in df.columns:
    omniscope_api.abort(f"Choose the text field (got '{field}').")
if not pattern:
    omniscope_api.abort("Enter a regular expression.")
flags = re.IGNORECASE if ignore_case else 0
try:
    rx = re.compile(pattern, flags)
except re.error as e:
    omniscope_api.abort(f"The regular expression is not valid: {e}")
    raise SystemExit

text = df[field].astype(object).where(df[field].notna(), None)
def as_text(v):
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))  # 123.0 in a decimal field reads as "123"
    return str(v)


s = pd.Series([as_text(v) for v in text], index=df.index, dtype=object)
out = df.copy()
user_names = [n.strip() for n in re.split(r"[,;\n]", names or "") if n.strip()]


def unique(name):
    base, k = name, 2
    while name in out.columns:
        name = f"{base} {k}"
        k += 1
    return name


if mode == "PARSE":
    if rx.groups == 0:
        omniscope_api.abort("Parse mode needs at least one capture group in brackets, for example (\\d+).")
    ex = s.str.extract(rx)
    group_names = {v: k for k, v in rx.groupindex.items()}
    cols = []
    for i in range(rx.groups):
        nm = user_names[i] if i < len(user_names) else group_names.get(i + 1, f"{field} {i + 1}")
        cols.append(unique(nm))
        out[cols[-1]] = ex.iloc[:, i].astype(object).where(ex.iloc[:, i].notna(), None)
    matched = ex.notna().any(axis=1)
    summary = f"{int(matched.sum()):,} of {len(df):,} rows matched; {len(cols)} field(s) parsed."
elif mode == "REPLACE":
    repl = re.sub(r"\$(\d+)", r"\\\1", replacement)  # allow $1 as well as \1
    try:
        new = s.map(lambda v: None if v is None else rx.sub(repl, v))
    except (re.error, IndexError) as e:
        omniscope_api.abort(f"The replacement text refers to a group that does not exist: {e}")
        raise SystemExit
    target = out_name or field
    out[target] = new.astype(object)
    changed = sum(1 for a, b in zip(s.tolist(), new.tolist()) if a != b)
    summary = f"{changed:,} of {len(df):,} values changed."
elif mode == "TOKENISE":
    found = s.map(lambda v: [] if v is None else [m.group(1) if rx.groups else m.group(0) for m in rx.finditer(v)])
    if tokenise_to == "ROWS":
        nm = unique(out_name or user_names[0] if (out_name or user_names) else f"{field} Token")
        rows_idx, toks, nums = [], [], []
        for i, lst in enumerate(found.tolist()):
            if lst:
                for k, t in enumerate(lst, 1):
                    rows_idx.append(i)
                    toks.append(t)
                    nums.append(k)
            elif keep_unmatched:
                rows_idx.append(i)
                toks.append(None)
                nums.append(None)
        out = df.iloc[rows_idx].reset_index(drop=True)
        out[nm] = pd.Series(toks, dtype=object)
        out["Token Number"] = pd.array(nums, dtype="Int64")
        summary = f"{sum(len(x) for x in found):,} tokens from {int((found.map(len) > 0).sum()):,} rows."
    else:
        for k in range(max_cols):
            nm = unique(user_names[k] if k < len(user_names) else f"{field} {k + 1}")
            out[nm] = pd.Series([lst[k] if len(lst) > k else None for lst in found.tolist()], index=df.index, dtype=object)
        extra = int((found.map(len) > max_cols).sum())
        summary = f"{sum(len(x) for x in found):,} tokens split into up to {max_cols} fields" + (f"; {extra:,} rows had more tokens than fields." if extra else ".")
elif mode == "MATCH":
    fn = {"FULL": lambda v: bool(rx.fullmatch(v)), "START": lambda v: bool(rx.match(v)), "CONTAINS": lambda v: bool(rx.search(v))}[match_type]
    nm = unique(out_name or f"{field} Matches")
    res = [None if v is None else ("Yes" if fn(v) else "No") for v in s.tolist()]
    out[nm] = pd.Series(res, index=df.index, dtype=object)
    summary = f"{res.count('Yes'):,} of {len(df):,} rows match."
else:
    omniscope_api.abort(f"Unknown mode {mode}")
    raise SystemExit

omniscope_api.write_output_records(out, output_number=0)
omniscope_api.close(summary)
