"""Period Comparison: the standard finance and trading pack layout, per group,
as at a reporting date: this month, prior month, same month last year,
year to date vs prior year to date, quarter to date, and moving annual total
(last 12 months) vs the 12 months before, with absolute and % variances. A
fiscal year can start in any month (April for many UK organisations).

Second output: a monthly trend table per group with last year's value, the
year-on-year change, the year-to-date cumulative and the moving annual total.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


date_f = opt("date_field")
value_f = opt("value_field")
group_fields = opt("group_fields", []) or []
as_of = opt("as_of", "")
fy_start = int(opt("fiscal_year_start", 1))
complete_only = opt("complete_months_only", True)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the transactions to the input.")
for f, label in ((date_f, "date"), (value_f, "value")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
miss = [g for g in group_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Group fields not in the input: {', '.join(miss)}")
if not 1 <= fy_start <= 12:
    omniscope_api.abort("Fiscal year start month must be 1 to 12.")


def to_date(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s
    else:
        txt = s.astype(object).where(s.notna(), None).astype(str).str.strip()
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        d = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        d[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
        d[~iso & s.notna()] = pd.to_datetime(txt[~iso & s.notna()], errors="coerce", dayfirst=True, format="mixed")
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    return d


w = pd.DataFrame({"d": to_date(df[date_f]), "v": pd.to_numeric(df[value_f], errors="coerce").fillna(0.0)})
for g in group_fields:
    w[g] = df[g].astype(object).where(df[g].notna(), "(blank)")
skipped = int(w["d"].isna().sum())
w = w.dropna(subset=["d"])
if w.empty:
    omniscope_api.abort("No valid dates in the input.")
w["m"] = w["d"].dt.to_period("M")

if as_of:
    ref = to_date(pd.Series([as_of], dtype=object)).iloc[0]
    if pd.isna(ref):
        omniscope_api.abort("Reporting date must be a date, such as 2025-10-31.")
    cur = ref.to_period("M")
else:
    last = w["d"].max()
    cur = last.to_period("M")
    if complete_only and last != cur.end_time.normalize() and last.normalize() != cur.end_time.normalize():
        cur = cur - 1  # latest month is incomplete: report the last full month


def fy_start_period(p):
    y = p.year if p.month >= fy_start else p.year - 1
    return pd.Period(year=y, month=fy_start, freq="M")


def q_start_period(p):
    offset = (p.month - fy_start) % 3
    return p - offset


fys = fy_start_period(cur)
qs = q_start_period(cur)
windows = {
    "Month": (cur, cur), "Prior Month": (cur - 1, cur - 1), "Same Month Last Year": (cur - 12, cur - 12),
    "QTD": (qs, cur), "Prior Year QTD": (qs - 12, cur - 12),
    "YTD": (fys, cur), "Prior YTD": (fys - 12, cur - 12),
    "MAT": (cur - 11, cur), "Prior MAT": (cur - 23, cur - 12),
}
monthly = w.groupby(list(group_fields) + ["m"])["v"].sum()
keys = list(monthly.index.droplevel("m").unique()) if group_fields else [()]
rows = []
for k in keys:
    s = monthly.loc[k] if group_fields else monthly
    if isinstance(s, (int, float, np.floating)):
        s = pd.Series([s])
    rec = {} if not group_fields else dict(zip(group_fields, k if isinstance(k, tuple) else (k,)))
    for name, (a, b) in windows.items():
        rec[name] = float(s[(s.index >= a) & (s.index <= b)].sum())
    for cur_n, base_n, label in (("Month", "Prior Month", "vs Prior Month"), ("Month", "Same Month Last Year", "vs Last Year"),
                                 ("QTD", "Prior Year QTD", "QTD vs Last Year"), ("YTD", "Prior YTD", "YTD vs Last Year"), ("MAT", "Prior MAT", "MAT vs Prior MAT")):
        rec[f"Change {label}"] = rec[cur_n] - rec[base_n]
        rec[f"% Change {label}"] = (rec[cur_n] / rec[base_n] - 1) if rec[base_n] else np.nan
    rows.append(rec)
summ = pd.DataFrame(rows)
summ.insert(len(group_fields), "Reporting Month", str(cur))
summ.insert(len(group_fields) + 1, "Fiscal Year Start", str(fys))
if group_fields:
    tot = {g: "Total" for g in group_fields}
    tot.update({"Reporting Month": str(cur), "Fiscal Year Start": str(fys)})
    for name in windows:
        tot[name] = float(summ[name].sum())
    for cur_n, base_n, label in (("Month", "Prior Month", "vs Prior Month"), ("Month", "Same Month Last Year", "vs Last Year"),
                                 ("QTD", "Prior Year QTD", "QTD vs Last Year"), ("YTD", "Prior YTD", "YTD vs Last Year"), ("MAT", "Prior MAT", "MAT vs Prior MAT")):
        tot[f"Change {label}"] = tot[cur_n] - tot[base_n]
        tot[f"% Change {label}"] = (tot[cur_n] / tot[base_n] - 1) if tot[base_n] else np.nan
    summ = pd.concat([summ, pd.DataFrame([tot])], ignore_index=True)
for c in summ.columns:
    if c not in group_fields and c not in ("Reporting Month", "Fiscal Year Start"):
        summ[c] = summ[c].astype("float64")

# trend table
trend_rows = []
all_m = pd.period_range(w["m"].min(), cur, freq="M")
for k in keys:
    s = (monthly.loc[k] if group_fields else monthly).reindex(all_m, fill_value=0.0)
    rec_base = {} if not group_fields else dict(zip(group_fields, k if isinstance(k, tuple) else (k,)))
    ly = s.shift(12)
    mat = s.rolling(12, min_periods=12).sum()
    fy = pd.Series([fy_start_period(p) for p in s.index], index=s.index)
    ytd = s.groupby(fy.values).cumsum()
    for p in s.index:
        trend_rows.append({**rec_base, "Month": str(p), "Month Start": p.start_time, "Value": float(s[p]),
                           "Same Month Last Year": float(ly[p]) if pd.notna(ly[p]) else np.nan,
                           "% Change vs Last Year": (s[p] / ly[p] - 1) if pd.notna(ly[p]) and ly[p] else np.nan,
                           "YTD": float(ytd[p]), "MAT": float(mat[p]) if pd.notna(mat[p]) else np.nan,
                           "Fiscal Year": f"FY {fy[p].year}/{str(fy[p].year + 1)[2:]}" if fy_start != 1 else str(fy[p].year)})
trend = pd.DataFrame(trend_rows)
trend["Month Start"] = pd.to_datetime(trend["Month Start"]).dt.tz_localize("UTC")
for c in ("Value", "Same Month Last Year", "% Change vs Last Year", "YTD", "MAT"):
    trend[c] = trend[c].astype("float64")

omniscope_api.write_output(summ, "comparison")
omniscope_api.write_output(trend, "trend")
omniscope_api.close(f"Reporting month {cur} (fiscal year from {fys}); {len(keys):,} group(s)"
                    + (f"; {skipped:,} rows without a valid date skipped." if skipped else "."))
