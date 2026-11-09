"""Imputation: fill missing values per field with the mean, median, mode, a
constant, the previous / next value or a linear interpolation, optionally
within groups (with a fall-back to the overall value), with "was imputed"
indicator fields and a summary of what was filled.
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
numeric_method = opt("numeric_method", "MEDIAN")
text_method = opt("text_method", "MODE")
constant_number = opt("constant_number", 0.0)
constant_text = opt("constant_text", "Unknown")
group_fields = opt("group_fields", []) or []
fallback = opt("fallback_overall", True)
order_fields = opt("order_fields", []) or []
add_flags = opt("add_flags", True)
extra_missing = opt("extra_missing", "")
keep_integers = opt("keep_integers", True)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
missing_fields = [f for f in list(fields) + list(group_fields) + list(order_fields) if f not in df.columns]
if missing_fields:
    omniscope_api.abort(f"Fields not in the input: {', '.join(missing_fields)}")


def is_num(s):
    return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


def is_txt(s):
    return pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)


sentinels = [t.strip() for t in re.split(r"[,;\n]", extra_missing or "") if t.strip()]
sent_num = []
for t in sentinels:
    try:
        sent_num.append(float(t))
    except ValueError:
        pass
sent_txt = {t.lower() for t in sentinels}

out = df.copy()
targets = list(fields) if fields else [c for c in df.columns if c not in group_fields and c not in order_fields]

# order for fill-forward / back / interpolation
order = np.arange(len(out))
if order_fields:
    order = out.sort_values(list(order_fields), kind="mergesort").index.to_numpy()

if group_fields:
    keys = [out[c].astype(object).where(out[c].notna(), "\u0000null") for c in group_fields]
else:
    keys = [pd.Series(0, index=out.index)]


def mode_of(s):
    m = s.dropna().mode()
    return m.iloc[0] if len(m) else np.nan


summary = []
for col in targets:
    s = out[col]
    num, txt = is_num(s), is_txt(s)
    if not (num or txt):
        continue
    method = numeric_method if num else text_method
    if method == "NONE":
        continue
    work = s.astype("float64") if num else s.astype(object)
    if num and sent_num:
        work = work.mask(work.isin(sent_num))
    if txt and sent_txt:
        work = work.mask(work.astype(str).str.strip().str.lower().isin(sent_txt))
    work = work.where(work.notna(), np.nan) if txt else work
    was_missing = work.isna()
    n_missing = int(was_missing.sum())
    filled = work.copy()
    value_used = ""
    if n_missing:
        if method in ("MEAN", "MEDIAN", "MODE"):
            fn = {"MEAN": "mean", "MEDIAN": "median"}.get(method)
            grp = work.groupby(keys, sort=False)
            stat = grp.transform(fn) if fn else grp.transform(mode_of)
            filled = work.fillna(stat)
            overall = (getattr(work, fn)() if fn else mode_of(work))
            if fallback:
                filled = filled.fillna(overall)
            if not group_fields:
                value_used = overall
        elif method == "CONSTANT":
            value_used = float(constant_number) if num else str(constant_text)
            filled = work.fillna(value_used)
        elif method in ("FFILL", "BFILL", "INTERPOLATE"):
            ordered = work.loc[order]
            okeys = [k.loc[order] for k in keys]
            g = ordered.groupby(okeys, sort=False)
            if method == "FFILL":
                res = g.ffill()
            elif method == "BFILL":
                res = g.bfill()
            else:
                res = g.transform(lambda x: x.interpolate(method="linear", limit_area="inside"))
            filled = res.reindex(work.index)
            if fallback and method == "INTERPOLATE":
                filled = filled.fillna(g.ffill().reindex(work.index)).fillna(g.bfill().reindex(work.index))
    if num:
        if keep_integers and pd.api.types.is_integer_dtype(s):
            filled = pd.array(np.round(filled.to_numpy(dtype="float64")), dtype="Float64").astype("Int64")
            if isinstance(value_used, float):
                value_used = round(value_used)
        out[col] = filled
    else:
        out[col] = filled.astype(object).where(filled.notna(), None)
    imputed = was_missing & pd.Series(out[col]).notna().to_numpy()
    if add_flags:
        out[f"{col} Was Imputed"] = pd.array(imputed.astype(int).to_numpy(), dtype="Int64")
    summary.append({"Field": str(col), "Type": "Number" if num else "Text",
                    "Method": method.title().replace("Ffill", "Previous value").replace("Bfill", "Next value"),
                    "Missing Before": n_missing, "Imputed": int(imputed.sum()),
                    "Still Missing": int(pd.Series(out[col]).isna().sum()),
                    "Value Used": "" if value_used == "" else str(round(value_used, 4) if isinstance(value_used, float) else value_used),
                    "Within Groups": ", ".join(group_fields) if method in ("MEAN", "MEDIAN", "MODE", "FFILL", "BFILL", "INTERPOLATE") and group_fields else ""})

rep = pd.DataFrame(summary, columns=["Field", "Type", "Method", "Missing Before", "Imputed", "Still Missing", "Value Used", "Within Groups"])
for c in ("Missing Before", "Imputed", "Still Missing"):
    rep[c] = rep[c].astype("int64")
omniscope_api.write_output(out, "imputed")
omniscope_api.write_output(rep, "summary")
omniscope_api.close(f"{int(rep['Imputed'].sum()):,} values imputed in {int((rep['Imputed'] > 0).sum())} fields; "
                    f"{int(rep['Still Missing'].sum()):,} still missing.")
