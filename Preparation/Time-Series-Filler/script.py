"""Time Series Filler: insert the missing periods (days, weeks, months...) in
each series so every series has one row per period, fill the value fields
(zero, previous value, linear interpolation or leave empty) and report the
gaps found per series.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


date_field = opt("date_field")
group_fields = opt("group_fields", []) or []
value_fields = opt("value_fields", []) or []
frequency = opt("frequency", "DAY")
fill_method = opt("fill_method", "ZERO")
span = opt("span", "SERIES")
range_start = opt("range_start", "")
range_end = opt("range_end", "")
carry_other = opt("carry_other", True)
day_first = opt("day_first", True)

FREQ = {"HOUR": "h", "DAY": "D", "WEEK": "W-SUN", "MONTH": "M", "QUARTER": "Q-DEC", "YEAR": "Y-DEC"}

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the time series data to the input.")
if not date_field or date_field not in df.columns:
    omniscope_api.abort(f"Choose the date field (got '{date_field}').")
miss = [f for f in list(group_fields) + list(value_fields) if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")
if frequency not in FREQ:
    omniscope_api.abort(f"Unknown frequency {frequency}")


def to_date(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s
    else:
        txt = s.astype(object).where(s.notna(), None).astype(str).str.strip()
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        d = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        if iso.any():
            d[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
        rest = ~iso & s.notna()
        if rest.any():
            d[rest] = pd.to_datetime(txt[rest], errors="coerce", dayfirst=bool(day_first), format="mixed")
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    return d


freq = FREQ[frequency]
orig_tz = df[date_field].dt.tz if pd.api.types.is_datetime64_any_dtype(df[date_field]) else None
dates = to_date(df[date_field])
work = df.copy()
if pd.api.types.is_datetime64_any_dtype(df[date_field]):
    work[date_field] = dates  # time-zone naive inside; restored on output
work["__period"] = dates.dt.to_period(freq)
bad_dates = int(work["__period"].isna().sum())
valid = work[work["__period"].notna()].copy()
invalid = work[work["__period"].isna()].copy()

glob_lo = glob_hi = None
if span == "CUSTOM":
    try:
        rs = to_date(pd.Series([range_start or None, range_end or None], dtype=object))
        if (range_start and pd.isna(rs.iloc[0])) or (range_end and pd.isna(rs.iloc[1])):
            raise ValueError("bad date")
        glob_lo = pd.Period(rs.iloc[0], freq) if range_start else None
        glob_hi = pd.Period(rs.iloc[1], freq) if range_end else None
    except (ValueError, TypeError):
        omniscope_api.abort("Start and end of the custom range must be dates, such as 2025-01-01.")
elif span == "ALL" and len(valid):
    glob_lo, glob_hi = valid["__period"].min(), valid["__period"].max()

if group_fields:
    keys = [valid[c].astype(object).where(valid[c].notna(), "\u0000null") for c in group_fields]
    grouped = valid.groupby(keys, sort=True)
    group_items = list(grouped.indices.items())
else:
    group_items = [(None, np.arange(len(valid)))]

parts, gaps = [], []
num_fill = [f for f in value_fields if pd.api.types.is_numeric_dtype(df[f]) and not pd.api.types.is_bool_dtype(df[f])]
for key, idx in group_items:
    g = valid.iloc[idx].copy()
    if g.empty:
        continue
    lo = glob_lo if glob_lo is not None else g["__period"].min()
    hi = glob_hi if glob_hi is not None else g["__period"].max()
    if span == "CUSTOM":
        g = g[(g["__period"] >= lo) & (g["__period"] <= hi)]
    if lo > hi:
        continue
    full = pd.period_range(lo, hi, freq=freq)
    present = pd.Index(g["__period"].unique())
    missing = full.difference(present)
    filler = pd.DataFrame({"__period": missing})
    if len(group_fields):
        first = valid.iloc[idx].iloc[0]
        for c in group_fields:
            filler[c] = first[c]
    filler["__filled"] = 1
    g["__filled"] = 0
    comb = pd.concat([g, filler], ignore_index=True, sort=False)
    comb = comb.sort_values(["__period", "__filled"], kind="mergesort").reset_index(drop=True)
    comb[date_field] = comb[date_field].where(comb["__filled"] == 0, comb["__period"].dt.start_time)
    if carry_other:
        others = [c for c in df.columns if c not in group_fields and c not in value_fields and c != date_field]
        if others:
            comb[others] = comb[others].ffill().bfill()
    for f in value_fields:
        if fill_method == "LEAVE":
            continue
        if f in num_fill:
            s = comb[f].astype("float64")
            if fill_method == "ZERO":
                s = s.where(comb["__filled"] == 0, 0.0)
            elif fill_method == "PREVIOUS":
                s = s.where(comb["__filled"] == 0).ffill()
            elif fill_method == "LINEAR":
                ordinal = comb["__period"].map(lambda p: p.ordinal).astype("float64")
                known = comb["__filled"] == 0
                s_known = s.where(known)
                ok = s_known.notna()
                if ok.sum() >= 2:
                    interp = np.interp(ordinal, ordinal[ok], s_known[ok])
                    s = s.where(known, pd.Series(interp, index=s.index))
                    beyond = (ordinal < ordinal[ok].min()) | (ordinal > ordinal[ok].max())
                    s = s.where(~(beyond & ~known))
            comb[f] = s
        else:  # text value fields: carry the previous value for inserted rows
            if fill_method in ("PREVIOUS", "LINEAR"):
                comb[f] = comb[f].where(comb["__filled"] == 0, comb[f].where(comb["__filled"] == 0).ffill())
    parts.append(comb)
    # longest run of missing periods
    is_missing = full.isin(missing)
    longest, run = 0, 0
    for m in is_missing:
        run = run + 1 if m else 0
        longest = max(longest, run)
    row = {c: valid.iloc[idx].iloc[0][c] for c in group_fields}
    row.update({"First Period": str(lo), "Last Period": str(hi), "Expected Periods": len(full),
                "Periods Present": int(len(present.intersection(full))), "Periods Inserted": int(len(missing)),
                "Longest Gap (periods)": int(longest),
                "Completeness": (len(full) - len(missing)) / len(full) if len(full) else np.nan})
    gaps.append(row)

if parts:
    out = pd.concat(parts, ignore_index=True, sort=False)
else:
    out = valid.assign(__filled=pd.Series([], dtype="int64"))
if len(invalid):
    invalid["__filled"] = 0
    out = pd.concat([out, invalid], ignore_index=True, sort=False)
out["Period"] = out["__period"].astype(object).map(lambda p: None if p is None or p is pd.NaT or (isinstance(p, float) and p != p) else str(p)).astype(object)
out["Is Inserted"] = pd.array(out["__filled"].astype("Int64"), dtype="Int64")
out = out.drop(columns=["__period", "__filled"])
for f in value_fields:
    if f in num_fill and pd.api.types.is_integer_dtype(df[f]) and fill_method in ("ZERO", "PREVIOUS"):
        out[f] = pd.array(np.round(pd.to_numeric(out[f], errors="coerce").to_numpy(dtype=float)), dtype="Float64").astype("Int64")
if pd.api.types.is_datetime64_any_dtype(df[date_field]) or out[date_field].map(lambda v: isinstance(v, pd.Timestamp)).any():
    out[date_field] = to_date(out[date_field].map(lambda v: v.tz_localize(None) if isinstance(v, pd.Timestamp) and v.tzinfo else v).astype(object))
    if orig_tz is not None:
        out[date_field] = out[date_field].dt.tz_localize(orig_tz)
for c in df.columns:
    if pd.api.types.is_integer_dtype(df[c]) and c in out.columns and not pd.api.types.is_integer_dtype(out[c]):
        out[c] = pd.array(pd.to_numeric(out[c], errors="coerce").to_numpy(dtype=float), dtype="Float64").round().astype("Int64")

gap_cols = list(group_fields) + ["First Period", "Last Period", "Expected Periods", "Periods Present", "Periods Inserted",
                                 "Longest Gap (periods)", "Completeness"]
gap_df = pd.DataFrame(gaps, columns=gap_cols)
for c in ("Expected Periods", "Periods Present", "Periods Inserted", "Longest Gap (periods)"):
    gap_df[c] = gap_df[c].astype("int64")
gap_df["Completeness"] = gap_df["Completeness"].astype("float64")

omniscope_api.write_output(out, "filled")
omniscope_api.write_output(gap_df, "gaps")
inserted = int(gap_df["Periods Inserted"].sum())
omniscope_api.close(f"{inserted:,} missing {frequency.lower()} periods inserted across {len(gap_df):,} series"
                    + (f"; {bad_dates:,} rows had no valid date and were passed through." if bad_dates else "."))
