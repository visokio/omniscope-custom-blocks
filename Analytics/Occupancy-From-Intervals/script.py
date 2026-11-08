"""Occupancy From Intervals: how many things are "in" at once, over time, from
start and end times: beds in a ward, cars in a car park, staff on site,
concurrent users, rooms booked, machines running.

Per group (ward, site, car park) and time bucket (15 minutes, hour, day):
average occupancy (time-weighted), peak occupancy, arrivals and departures,
and utilisation against a capacity. Per group: overall peak and when it
happened, average occupancy, utilisation and time spent over capacity.
An optional weight counts each interval as several (people in a booking).
Intervals with no end are treated as still in progress at the as-of time.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


start_f, end_f = opt("start_field"), opt("end_field")
group_f, weight_f = opt("group_field"), opt("weight_field")
bucket = opt("bucket", "HOUR")
cap_default = float(opt("capacity", 0) or 0)
cap_txt = opt("capacity_by_group", "")
as_of_txt = opt("as_of", "")
STEP = {"15MIN": pd.Timedelta(minutes=15), "HOUR": pd.Timedelta(hours=1), "DAY": pd.Timedelta(days=1)}[bucket]

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the intervals (start and end times) to the input.")
for f, lab in ((start_f, "start"), (end_f, "end")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} time field (got '{f}').")
for f in (group_f, weight_f):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")


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


caps = {}
for part in [p.strip() for p in re.split(r"[,;\n]", cap_txt or "") if p.strip()]:
    m = re.match(r"^(.*?)\s*[=:]\s*([\d.]+)$", part)
    if not m:
        omniscope_api.abort(f"Could not read '{part}' in capacity by group; use pairs such as Ward A=24.")
    caps[m.group(1).strip().lower()] = float(m.group(2))
st, en = to_ts(df[start_f]), to_ts(df[end_f])
as_of = to_ts(pd.Series([as_of_txt], dtype=object)).iloc[0] if as_of_txt else max(st.max(), en.max()) if st.notna().any() else pd.NaT
if as_of_txt and pd.isna(as_of):
    omniscope_api.abort("The 'as of' time must be a date and time, such as 2025-11-30 23:59.")
en = en.where(en.notna(), as_of)
wt = pd.to_numeric(df[weight_f], errors="coerce").fillna(1.0).astype("float64") if weight_f else pd.Series(1.0, index=df.index)
grp = df[group_f].astype(object).where(df[group_f].notna(), "(blank)").map(str) if group_f else pd.Series("All", index=df.index)
ok = st.notna() & en.notna() & (en >= st)
bad = int((~ok).sum())
W = pd.DataFrame({"g": grp[ok], "s": st[ok], "e": en[ok], "w": wt[ok]})

orows, srows = [], []
for g, d in W.groupby("g", sort=True):
    cap = caps.get(g.lower(), cap_default)
    t0 = d["s"].min().floor(STEP if bucket != "DAY" else "D")
    t1 = d["e"].max()
    edges = pd.date_range(t0, t1.ceil(STEP if bucket != "DAY" else "D") + (STEP if t1 == t1.ceil(STEP if bucket != 'DAY' else 'D') else pd.Timedelta(0)), freq=STEP)
    if len(edges) < 2:
        edges = pd.DatetimeIndex([t0, t0 + STEP])
    ev_t = np.concatenate([d["s"].to_numpy(), d["e"].to_numpy()])
    ev_w = np.concatenate([d["w"].to_numpy(), -d["w"].to_numpy()])
    # breakpoints: event times plus bucket edges; level is constant between consecutive breakpoints
    bp = np.unique(np.concatenate([ev_t, edges.to_numpy()]))
    order = np.argsort(ev_t, kind="mergesort")
    cum = np.cumsum(ev_w[order])
    idx = np.searchsorted(ev_t[order], bp, side="right") - 1
    level = np.where(idx >= 0, cum[np.clip(idx, 0, None)], 0.0)       # occupancy from bp[i] to bp[i+1]
    seg_len = np.diff(bp).astype("timedelta64[s]").astype(float)
    seg_lvl = level[:-1]
    seg_bucket = np.searchsorted(edges.to_numpy(), bp[:-1], side="right") - 1
    nb = len(edges) - 1
    area = np.bincount(seg_bucket, weights=seg_lvl * seg_len, minlength=nb)[:nb]
    peak = np.full(nb, 0.0)
    np.maximum.at(peak, seg_bucket[seg_bucket < nb], seg_lvl[seg_bucket < nb])
    blen = STEP.total_seconds()
    arr = np.bincount(np.searchsorted(edges.to_numpy(), d["s"].to_numpy(), side="right") - 1, weights=d["w"].to_numpy(), minlength=nb)[:nb]
    dep_idx = np.searchsorted(edges.to_numpy(), d["e"].to_numpy(), side="right") - 1
    dep = np.bincount(np.clip(dep_idx, 0, nb - 1), weights=d["w"].to_numpy(), minlength=nb)[:nb]
    for b in range(nb):
        orows.append({"Group": g, "Bucket Start": edges[b], "Average Occupancy": area[b] / blen, "Peak Occupancy": float(peak[b]), "Arrivals": float(arr[b]),
                      "Departures": float(dep[b]), "Capacity": cap if cap > 0 else np.nan, "Utilisation": (area[b] / blen / cap) if cap > 0 else np.nan,
                      "Over Capacity": ("Yes" if peak[b] > cap else "No") if cap > 0 else None})
    pk = float(seg_lvl.max()) if len(seg_lvl) else 0.0
    pk_at = bp[:-1][int(np.argmax(seg_lvl))] if len(seg_lvl) else pd.NaT
    total_t = seg_len.sum()
    over = float(seg_len[seg_lvl > cap].sum()) / 3600 if cap > 0 else np.nan
    srows.append({"Group": g, "Intervals": int(len(d)), "From": d["s"].min(), "To": d["e"].max(), "Peak Occupancy": pk, "Peak First Reached": pd.Timestamp(pk_at),
                  "Average Occupancy": float((seg_lvl * seg_len).sum() / total_t) if total_t else np.nan, "Capacity": cap if cap > 0 else np.nan,
                  "Average Utilisation": float((seg_lvl * seg_len).sum() / total_t / cap) if total_t and cap > 0 else np.nan, "Hours Over Capacity": over,
                  "Median Duration Hours": float(((d["e"] - d["s"]).dt.total_seconds() / 3600).median())})
occ = pd.DataFrame(orows, columns=["Group", "Bucket Start", "Average Occupancy", "Peak Occupancy", "Arrivals", "Departures", "Capacity", "Utilisation", "Over Capacity"])
summ = pd.DataFrame(srows, columns=["Group", "Intervals", "From", "To", "Peak Occupancy", "Peak First Reached", "Average Occupancy", "Capacity", "Average Utilisation",
                                    "Hours Over Capacity", "Median Duration Hours"])
for t in (occ, summ):
    for c in t.columns:
        if c in ("Bucket Start", "From", "To", "Peak First Reached"):
            t[c] = pd.to_datetime(t[c]).dt.tz_localize("UTC")
        elif c not in ("Group", "Over Capacity", "Intervals"):
            t[c] = t[c].astype("float64")
summ["Intervals"] = summ["Intervals"].astype("int64")
if group_f:
    occ = occ.rename(columns={"Group": str(group_f)})
    summ = summ.rename(columns={"Group": str(group_f)})
omniscope_api.write_output(occ, "occupancy")
omniscope_api.write_output(summ, "summary")
omniscope_api.close(f"{int(ok.sum()):,} intervals in {len(summ):,} group(s), {len(occ):,} {bucket.lower()} buckets"
                    + (f"; highest peak {summ['Peak Occupancy'].max():g}" if len(summ) else "") + (f"; {bad:,} intervals without valid times skipped" if bad else "") + ".")
