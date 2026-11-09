"""Date Range Expander: turn each record with a start and end date into one
row per day, week, month, quarter or year it covers, with the number of days
in each period and amounts prorated by days.

Typical pattern: generate rows, then formulas (and a summary).
Vectorised with pandas Periods, so 100k records x 36 months is fine.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


start_field = opt("start_field")
end_field = opt("end_field")
frequency = opt("frequency", "MONTH")
prorate_fields = opt("prorate_fields", []) or []
inclusive_end = opt("inclusive_end", True)
missing_end = opt("missing_end", "TODAY")
day_first = opt("day_first", True)
max_periods = int(opt("max_periods", 5000))

FREQ = {"DAY": "D", "WEEK": "W-SUN", "MONTH": "M", "QUARTER": "Q-DEC", "YEAR": "Y-DEC"}
LABEL = {"DAY": "%Y-%m-%d", "WEEK": None, "MONTH": "%Y-%m", "QUARTER": None, "YEAR": "%Y"}

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect records with a start and end date to the input.")
for f, label in ((start_field, "Start date"), (end_field, "End date")):
    if not f:
        omniscope_api.abort(f"Choose the {label.lower()} field.")
    if f not in df.columns:
        omniscope_api.abort(f"{label} field '{f}' is not in the input.")
missing = [f for f in prorate_fields if f not in df.columns]
if missing:
    omniscope_api.abort(f"Fields to prorate not in the input: {', '.join(missing)}")
if frequency not in FREQ:
    omniscope_api.abort(f"Unknown frequency {frequency}")


def to_date(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s
    else:
        txt = s.astype(object).where(s.notna(), None).astype(str).str.strip()
        # ISO dates (2025-02-01) must never be read day first: pandas would make it 2 January
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        d = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        if iso.any():
            d[iso] = pd.to_datetime(txt[iso].str[:10], errors="coerce", format="%Y-%m-%d")
        rest = ~iso & s.notna()
        if rest.any():
            d[rest] = pd.to_datetime(txt[rest], errors="coerce", dayfirst=bool(day_first), format="mixed")
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    return d.dt.normalize()


start = to_date(df[start_field])
end = to_date(df[end_field])
if missing_end == "TODAY":
    end = end.fillna(pd.Timestamp.today().normalize())
elif missing_end == "START":
    end = end.where(end.notna(), start)
if not inclusive_end:
    end = end - pd.Timedelta(days=1)

reason = pd.Series("", index=df.index, dtype=object)
reason[start.isna()] = "Start date missing or not a date"
reason[(reason == "") & end.isna()] = "End date missing or not a date"
reason[(reason == "") & (end < start)] = "End date before start date"

freq = FREQ[frequency]
ok = reason == ""
n_periods = pd.Series(0, index=df.index, dtype="int64")
if ok.any():
    sp = start[ok].dt.to_period(freq)
    ep = end[ok].dt.to_period(freq)
    s_ord = sp.array.asi8
    e_ord = ep.array.asi8
    n_periods[ok] = e_ord - s_ord + 1
too_many = ok & (n_periods > max_periods)
reason[too_many] = f"More than {max_periods:,} periods (raise the limit option)"
ok = reason == ""

idx = np.flatnonzero(ok.values)
counts = n_periods.values[idx]
rep_idx = np.repeat(idx, counts)
offsets = np.arange(len(rep_idx)) - np.repeat(np.cumsum(counts) - counts, counts)

out = df.iloc[rep_idx].reset_index(drop=True)
s_rep = start.values[rep_idx]
e_rep = end.values[rep_idx]
first_ord = start.iloc[idx].dt.to_period(freq).array.asi8 if len(idx) else np.array([], dtype="int64")
ords = np.repeat(first_ord, counts) + offsets
periods = pd.PeriodIndex.from_ordinals(ords, freq=freq)
p_start = periods.start_time.normalize().values
p_end = periods.end_time.normalize().values

ov_start = np.maximum(s_rep, p_start)
ov_end = np.minimum(e_rep, p_end)
days = ((ov_end - ov_start) / np.timedelta64(1, "D")).astype("int64") + 1
total_days = ((e_rep - s_rep) / np.timedelta64(1, "D")).astype("int64") + 1
fraction = days / np.where(total_days == 0, 1, total_days)

if LABEL[frequency]:
    label = pd.DatetimeIndex(p_start).strftime(LABEL[frequency])
elif frequency == "WEEK":
    label = "w/c " + pd.DatetimeIndex(p_start).strftime("%Y-%m-%d")
else:
    label = [f"{p.year} Q{p.quarter}" for p in periods]

out["Period"] = list(label)
out["Period Start"] = pd.to_datetime(p_start)
out["Period End"] = pd.to_datetime(p_end)
out["Period Number"] = pd.array(offsets + 1, dtype="Int64")
out["Days In Period"] = pd.array(days, dtype="Int64")
out["Days In Range"] = pd.array(total_days, dtype="Int64")
out["Share Of Range"] = pd.Series(np.round(fraction, 6), dtype="float64")
for f in prorate_fields:
    vals = pd.to_numeric(df[f], errors="coerce").astype("float64").values[rep_idx]
    out[f"{f} (prorated)"] = pd.Series(np.round(vals * fraction, 6), dtype="float64")

skipped = df[~ok.values].reset_index(drop=True).copy()
skipped["Reason"] = reason[~ok].tolist()

omniscope_api.write_output(out, "expanded")
omniscope_api.write_output(skipped, "skipped")
omniscope_api.close(f"{int(ok.sum()):,} records expanded into {len(out):,} {frequency.lower()} rows; "
                    f"{len(skipped):,} skipped.")
