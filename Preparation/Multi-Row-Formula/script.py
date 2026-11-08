"""Multi-Row Formula: window calculations across rows, per group and in a
chosen order: previous / next value, change and % change, running total,
rolling mean / sum / min / max over N rows or N days, row number, rank and
share of group total.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


value_fields = opt("value_fields", []) or []
group_fields = opt("group_fields", []) or []
sort_fields = opt("sort_fields", []) or []
descending = opt("descending", False)
keep_order = opt("keep_order", True)
offset = int(opt("offset", 1))
window = int(opt("window", 7))
window_unit = opt("window_unit", "ROWS")
full_window = opt("full_window", False)

calcs = {k: bool(opt(k, False)) for k in (
    "calc_previous", "calc_next", "calc_change", "calc_pct_change", "calc_running_total",
    "calc_rolling_mean", "calc_rolling_sum", "calc_rolling_min", "calc_rolling_max",
    "calc_rank", "calc_share")}
row_number = opt("calc_row_number", False)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
if not value_fields and not row_number:
    omniscope_api.abort("Choose at least one value field (or tick Row number).")
missing = [f for f in list(value_fields) + list(group_fields) + list(sort_fields) if f not in df.columns]
if missing:
    omniscope_api.abort(f"Fields not in the input: {', '.join(missing)}")
if not any(calcs.values()) and not row_number:
    omniscope_api.abort("Tick at least one calculation.")
if window_unit == "DAYS" and (calcs["calc_rolling_mean"] or calcs["calc_rolling_sum"] or
                              calcs["calc_rolling_min"] or calcs["calc_rolling_max"]):
    if len(sort_fields) != 1:
        omniscope_api.abort("A rolling window in days needs exactly one sort field holding the date.")

work = df.copy()
work["__row"] = np.arange(len(work))
date_key = None
if window_unit == "DAYS" and sort_fields:
    d = work[sort_fields[0]]
    if not pd.api.types.is_datetime64_any_dtype(d):
        txt = d.astype(object).where(d.notna(), None).astype(str)
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        parsed = pd.Series(pd.NaT, index=d.index, dtype="datetime64[ns]")
        parsed[iso] = pd.to_datetime(txt[iso].str[:19], errors="coerce", format="mixed")
        parsed[~iso & d.notna()] = pd.to_datetime(txt[~iso & d.notna()], errors="coerce", dayfirst=True, format="mixed")
        d = parsed
    work["__date"] = d
    date_key = "__date"
    sort_cols = ["__date"]
else:
    sort_cols = list(sort_fields)

order_cols = list(group_fields) + sort_cols + ["__row"]
asc = [True] * len(group_fields) + [not descending] * len(sort_cols) + [True]
work = work.sort_values(order_cols, ascending=asc, kind="mergesort", na_position="last").reset_index(drop=True)

if group_fields:
    keys = [work[c].astype(object).where(work[c].notna(), "\u0000null") for c in group_fields]
else:
    keys = [pd.Series(0, index=work.index)]


def grp(series):
    return series.groupby(keys, sort=False)


g = grp(work["__row"])

if row_number:
    work["Row Number"] = pd.array(g.cumcount().to_numpy() + 1, dtype="Int64")

rolling_label = f"{window} days" if window_unit == "DAYS" else f"{window} rows"
skipped_text = []


def rolling(vals, how):
    minp = window if (full_window and window_unit == "ROWS") else 1
    if window_unit == "DAYS":
        res = pd.Series(np.nan, index=work.index)
        for _, idx in g.indices.items():  # positions of each group's rows
            dates = work[date_key].iloc[idx]
            valid = dates.notna()
            if not valid.any():
                continue
            s = pd.Series(vals.iloc[idx][valid.to_numpy()].to_numpy(dtype=float), index=pd.DatetimeIndex(dates[valid]))
            r = getattr(s.rolling(f"{window}D", min_periods=1), how)()
            if full_window:
                span = (s.index - s.index.min()) >= pd.Timedelta(days=window - 1)
                r[~span] = np.nan
            res.loc[np.asarray(idx)[valid.to_numpy()]] = r.to_numpy()
        return res
    r = getattr(grp(vals).rolling(window, min_periods=minp), how)()
    return r.reset_index(level=list(range(r.index.nlevels - 1)), drop=True).sort_index()


for f in value_fields:
    numeric = pd.api.types.is_numeric_dtype(work[f]) and not pd.api.types.is_bool_dtype(work[f])
    if calcs["calc_previous"]:
        work[f"{f} Previous"] = grp(work[f]).shift(offset)
    if calcs["calc_next"]:
        work[f"{f} Next"] = grp(work[f]).shift(-offset)
    if not numeric:
        if any(calcs[k] for k in calcs if k not in ("calc_previous", "calc_next")):
            skipped_text.append(f)
        continue
    vals = work[f].astype("float64")
    gv = grp(vals)
    prev = gv.shift(offset)
    if calcs["calc_change"]:
        work[f"{f} Change"] = vals - prev
    if calcs["calc_pct_change"]:
        work[f"{f} % Change"] = np.where(prev.to_numpy() == 0, np.nan, (vals - prev) / prev.abs())
    if calcs["calc_running_total"]:
        work[f"{f} Running Total"] = gv.cumsum()
    for key, how, label in (("calc_rolling_mean", "mean", "Rolling Mean"), ("calc_rolling_sum", "sum", "Rolling Sum"),
                            ("calc_rolling_min", "min", "Rolling Min"), ("calc_rolling_max", "max", "Rolling Max")):
        if calcs[key]:
            work[f"{f} {label} ({rolling_label})"] = rolling(vals, how).to_numpy()
    if calcs["calc_rank"]:
        work[f"{f} Rank"] = pd.array(gv.rank(method="min", ascending=False).to_numpy(), dtype="Float64").astype("Int64")
    if calcs["calc_share"]:
        tot = gv.transform("sum")
        work[f"{f} Share Of Group"] = np.where(tot.to_numpy() == 0, np.nan, vals / tot)

if keep_order:
    work = work.sort_values("__row", kind="mergesort").reset_index(drop=True)
work = work.drop(columns=[c for c in ("__row", "__date") if c in work.columns])
for c in work.columns:
    if c not in df.columns and pd.api.types.is_float_dtype(work[c]):
        work[c] = work[c].astype("float64")

omniscope_api.write_output_records(work, output_number=0)
msg = f"{len(work):,} rows; {g.ngroups:,} groups."
if skipped_text:
    msg += f" Numeric calculations skipped for text fields: {', '.join(skipped_text)}."
omniscope_api.close(msg)
