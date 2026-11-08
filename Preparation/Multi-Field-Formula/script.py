"""Multi-Field Formula: apply the same operation to many fields at once, chosen
explicitly, by a name pattern (so new month columns are picked up
automatically) or as all number / text fields; replace them or add new fields;
optionally add row-wise totals (sum, mean, min, max, count) across them.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


fields = opt("fields", []) or []
pattern = opt("field_pattern", "")
type_filter = opt("type_filter", "ANY")
operation = opt("operation", "ROUND")
value = opt("value", 0.0)
decimals = int(opt("decimals", 2))
base_field = opt("base_field")
text_value = opt("text_value", "")
output = opt("output", "REPLACE")
suffix = opt("suffix", " (new)")
ROW_OPTS = {"SUM": opt("row_sum", False), "MEAN": opt("row_mean", False), "MIN": opt("row_min", False), "MAX": opt("row_max", False),
            "COUNT": opt("row_count", False), "STD": opt("row_std", False)}  # names written out so packaging checks can see them
row_stats = [k for k, on in ROW_OPTS.items() if on]

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
miss = [f for f in fields if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")


def is_num(s):
    return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


selected = list(fields)
if pattern:
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        omniscope_api.abort(f"Field name pattern is not a valid regular expression: {e}")
        raise SystemExit
    selected += [c for c in df.columns if rx.search(str(c)) and c not in selected]
if not fields and not pattern:
    selected = list(df.columns)
if type_filter == "NUMBER":
    selected = [c for c in selected if is_num(df[c])]
elif type_filter == "TEXT":
    selected = [c for c in selected if not is_num(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c])]
if not selected:
    omniscope_api.abort("No fields selected: choose fields, a name pattern or a type.")

NUM_OPS = {"ROUND", "MULTIPLY", "DIVIDE", "ADD", "SUBTRACT", "ROW_SHARE", "COLUMN_SHARE", "INDEX_TO_BASE", "DIFF_FROM_BASE",
           "ZSCORE", "MINMAX", "LOG", "ABS", "CLIP_MIN", "CLIP_MAX", "FILL", "TO_NUMBER", "NONE"}
TEXT_OPS = {"UPPER", "LOWER", "TITLE", "TRIM", "PREFIX", "SUFFIX", "FILL_TEXT", "LENGTH"}
if operation not in NUM_OPS | TEXT_OPS:
    omniscope_api.abort(f"Unknown operation {operation}")
if operation in ("INDEX_TO_BASE", "DIFF_FROM_BASE") and (not base_field or base_field not in df.columns):
    omniscope_api.abort("Choose the base field for index / difference operations.")

out = df.copy()
nums = {c: pd.to_numeric(df[c], errors="coerce").astype("float64") for c in selected}
skipped = []


def new_name(c):
    return c if output == "REPLACE" else f"{c}{suffix}"


if operation in NUM_OPS and operation != "NONE":
    if operation == "TO_NUMBER":
        targets = selected
    else:
        targets = [c for c in selected if is_num(df[c])]
        skipped = [c for c in selected if c not in targets]
    block = pd.DataFrame({c: nums[c] for c in targets}, index=df.index)
    if operation == "ROW_SHARE":
        tot = block.sum(axis=1, min_count=1)
        res = block.div(tot.where(tot != 0), axis=0)
    elif operation == "COLUMN_SHARE":
        res = block / block.sum().where(block.sum() != 0)
    elif operation in ("INDEX_TO_BASE", "DIFF_FROM_BASE"):
        base = pd.to_numeric(df[base_field], errors="coerce").astype("float64")
        res = block.div(base.where(base != 0), axis=0) * 100 if operation == "INDEX_TO_BASE" else block.sub(base, axis=0)
    elif operation == "ZSCORE":
        res = (block - block.mean()) / block.std(ddof=1).where(block.std(ddof=1) > 0)
    elif operation == "MINMAX":
        rng = block.max() - block.min()
        res = (block - block.min()) / rng.where(rng > 0)
    elif operation == "LOG":
        res = np.log(block.where(block > 0))
    else:
        v = float(value)
        res = {"ROUND": lambda b: b.round(decimals), "MULTIPLY": lambda b: b * v, "DIVIDE": lambda b: b / v if v else b * np.nan,
               "ADD": lambda b: b + v, "SUBTRACT": lambda b: b - v, "ABS": lambda b: b.abs(), "CLIP_MIN": lambda b: b.clip(lower=v),
               "CLIP_MAX": lambda b: b.clip(upper=v), "FILL": lambda b: b.fillna(v), "TO_NUMBER": lambda b: b}[operation](block)
    for c in targets:
        col = res[c]
        if operation in ("ROUND", "FILL", "CLIP_MIN", "CLIP_MAX", "ABS", "ADD", "SUBTRACT") and pd.api.types.is_integer_dtype(df[c]) and float(value).is_integer() \
                and (operation != "ROUND" or decimals <= 0):
            col = pd.array(col.round().to_numpy(), dtype="Float64").astype("Int64")
        elif operation == "TO_NUMBER" and col.dropna().apply(float.is_integer).all() and len(col.dropna()):
            col = pd.array(col.to_numpy(), dtype="Float64").astype("Int64")
        else:
            col = col.astype("float64")
        out[new_name(c)] = col
elif operation in TEXT_OPS:
    targets = [c for c in selected if not is_num(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c])]
    skipped = [c for c in selected if c not in targets]
    for c in targets:
        s = df[c].astype(object)
        mask = s.notna()
        t = s[mask].astype(str)
        if operation == "UPPER":
            t = t.str.upper()
        elif operation == "LOWER":
            t = t.str.lower()
        elif operation == "TITLE":
            t = t.str.title()
        elif operation == "TRIM":
            t = t.str.strip().str.replace(r"\s+", " ", regex=True)
        elif operation == "PREFIX":
            t = text_value + t
        elif operation == "SUFFIX":
            t = t + text_value
        elif operation == "LENGTH":
            ln = s.map(lambda v: len(str(v)) if v is not None and v == v else None)
            out[new_name(c)] = pd.array(ln.to_numpy(dtype=float), dtype="Float64").astype("Int64")
            continue
        new = pd.Series([None] * len(s), index=s.index, dtype=object)
        new[mask] = t.values
        if operation == "FILL_TEXT":
            new = new.where(new.notna(), text_value)
        out[new_name(c)] = new
else:
    targets = []

STAT = {"SUM": ("Row Sum", lambda b: b.sum(axis=1, min_count=1)), "MEAN": ("Row Mean", lambda b: b.mean(axis=1)),
        "MIN": ("Row Min", lambda b: b.min(axis=1)), "MAX": ("Row Max", lambda b: b.max(axis=1)),
        "COUNT": ("Row Count", lambda b: b.notna().sum(axis=1)), "STD": ("Row Std Dev", lambda b: b.std(axis=1, ddof=1))}
if row_stats:
    num_cols = [c for c in selected if is_num(df[c]) or operation == "TO_NUMBER"]
    src = pd.DataFrame({c: pd.to_numeric(out[new_name(c)] if new_name(c) in out.columns else df[c], errors="coerce").astype("float64")
                        for c in num_cols}, index=df.index) if num_cols else pd.DataFrame(index=df.index)
    for st in row_stats:
        if st not in STAT:
            continue
        nm, fn = STAT[st]
        if src.shape[1] == 0:
            continue
        col = fn(src)
        out[nm] = pd.array(col.to_numpy(), dtype="Int64") if st == "COUNT" else col.astype("float64")

omniscope_api.write_output_records(out, output_number=0)
msg = f"{operation.replace('_', ' ').lower()} applied to {len(targets)} field(s)"
if skipped:
    msg += f"; skipped (wrong type): {', '.join(map(str, skipped[:5]))}" + ("..." if len(skipped) > 5 else "")
omniscope_api.close(msg + (f"; row {', '.join(s.lower() for s in row_stats)} added." if row_stats else "."))
