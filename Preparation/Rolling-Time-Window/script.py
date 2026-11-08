"""Rolling Time Window: for every row, aggregate the rows of the same key that
fall within a trailing time window ending at its timestamp: transactions in
the last 24 hours per card, orders in the last 30 days per customer, alarms in
the last hour per machine. Unlike row-based moving windows, the window is
measured in time, so irregular data is handled correctly.

Per window: count, sum, mean, minimum and maximum of a value field, and the
number of distinct values of an optional field (for example distinct
merchants). Several windows can be computed at once. The current row can be
included or excluded (excluded is typical for fraud features).
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


key_f, time_f, val_f, dist_f = opt("key_field"), opt("time_field"), opt("value_field"), opt("distinct_field")
windows_txt = opt("windows", "1h, 24h, 7d, 30d")
include_current = bool(opt("include_current", True))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
for f, lab in ((key_f, "key"), (time_f, "timestamp")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
for f in (val_f, dist_f):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")
UNITS = {"m": "min", "min": "min", "h": "h", "d": "D", "w": "W"}
wins = []
for part in [p.strip() for p in re.split(r"[,;\s]+", windows_txt or "") if p.strip()]:
    m = re.fullmatch(r"(\d+)\s*(min|m|h|d|w)", part.lower())
    if not m:
        omniscope_api.abort(f"Could not read the window '{part}'; use for example 30min, 1h, 24h, 7d, 4w.")
    wins.append((part, pd.Timedelta(int(m.group(1)), unit=UNITS[m.group(2)] if UNITS[m.group(2)] != "W" else "D") * (7 if m.group(2) == "w" else 1)))
if not wins:
    omniscope_api.abort("Give at least one window, for example 24h, 7d.")


def to_ts(s):
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
    return d.astype("datetime64[ns]")


t = to_ts(df[time_f]).to_numpy()
k = df[key_f].astype(object).where(df[key_f].notna(), "(blank)").map(str).to_numpy()
v = pd.to_numeric(df[val_f], errors="coerce").astype("float64").to_numpy() if val_f else np.ones(len(df))
dv = df[dist_f].astype(object).where(df[dist_f].notna(), None).map(lambda x: None if x is None else str(x)).to_numpy() if dist_f else None
ok = ~np.isnat(t)
order = np.lexsort((np.arange(len(df)), t, k))
order = order[ok[order]]
out = df.copy()
res = {lab: {s: np.full(len(df), np.nan) for s in ("count", "sum", "mean", "min", "max", "distinct")} for lab, _ in wins}
ks, ts, vs = k[order], t[order], v[order]
bounds = np.flatnonzero(np.r_[True, ks[1:] != ks[:-1], True])
for a, b in zip(bounds[:-1], bounds[1:]):
    tt, vv = ts[a:b], vs[a:b]
    rows = order[a:b]
    csum = np.concatenate([[0.0], np.cumsum(np.nan_to_num(vv))])
    ccnt = np.concatenate([[0], np.cumsum(~np.isnan(vv))])
    for lab, td in wins:
        lo = np.searchsorted(tt, tt - td, side="right")          # window (t - td, t]
        hi = np.arange(1, len(tt) + 1) if include_current else np.arange(0, len(tt))
        # rows with the same timestamp as the current one count as "at" it: include them up to the current row only
        cnt = ccnt[hi] - ccnt[np.minimum(lo, hi)]
        sm = csum[hi] - csum[np.minimum(lo, hi)]
        r = res[lab]
        r["count"][rows] = cnt
        r["sum"][rows] = sm
        r["mean"][rows] = np.where(cnt > 0, sm / np.where(cnt > 0, cnt, 1), np.nan)
        if len(tt) <= 50_000:
            for j in range(len(tt)):
                seg = vv[lo[j]:hi[j]] if hi[j] > lo[j] else vv[:0]
                seg = seg[~np.isnan(seg)]
                r["min"][rows[j]] = seg.min() if len(seg) else np.nan
                r["max"][rows[j]] = seg.max() if len(seg) else np.nan
                if dv is not None:
                    dd = dv[rows][lo[j]:hi[j]] if hi[j] > lo[j] else []
                    r["distinct"][rows[j]] = len({x for x in dd if x is not None})
for lab, _ in wins:
    r = res[lab]
    out[f"Count {lab}"] = pd.array(np.where(ok, r["count"], np.nan), dtype="Float64").astype("Int64")
    if val_f:
        out[f"Sum {lab}"] = r["sum"]
        out[f"Mean {lab}"] = r["mean"]
        out[f"Min {lab}"] = r["min"]
        out[f"Max {lab}"] = r["max"]
    if dist_f:
        out[f"Distinct {dist_f} {lab}"] = pd.array(r["distinct"], dtype="Float64").astype("Int64")
for c in out.columns[len(df.columns):]:
    if str(out[c].dtype) not in ("Int64",):
        out[c] = out[c].astype("float64")
omniscope_api.write_output(out, "rows")
omniscope_api.close(f"{int(ok.sum()):,} rows, {len(bounds) - 1:,} keys, windows {', '.join(l for l, _ in wins)} ({'including' if include_current else 'excluding'} the current row)"
                    + (f"; {int((~ok).sum()):,} rows without a valid time" if (~ok).any() else "") + ".")
