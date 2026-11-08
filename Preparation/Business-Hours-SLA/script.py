"""Business Hours and SLA: elapsed working time between two timestamps (opened
and resolved), counting only opening hours on working days and skipping public
holidays, and whether each item met its service level.

  Opening hours such as 09:00 to 17:30, working days (Monday to Friday by
  default), public holidays for England and Wales, Scotland, Northern Ireland,
  US federal or none, plus your own closure dates.
  SLA targets in business hours: from a field, or by priority ("P1=4, P2=8,
  P3=24"), or one value for all. Items still open are measured to the as-of
  time. Each row gets its SLA due time, status (Met, Breached, Open, Open and
  breached) and business hours to spare or over.
"""
import datetime as dt
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


start_f, end_f = opt("start_field"), opt("end_field")
sla_f, prio_f = opt("sla_field"), opt("priority_field")
sla_map_txt = opt("sla_by_priority", "")
sla_default = float(opt("sla_hours", 0) or 0)
open_t, close_t = opt("open_time", "09:00"), opt("close_time", "17:30")
weekend = opt("weekend", "SAT_SUN")
region = opt("region", "ENGLAND_WALES")
custom_holidays = opt("custom_holidays", "")
as_of_txt = opt("as_of", "")

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the tickets or cases to the input.")
for f, lab in ((start_f, "start (opened) time"),):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
for f in (end_f, sla_f, prio_f):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")


def hm(t):
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(t))
    if not m or int(m.group(1)) > 24 or int(m.group(2)) > 59:
        omniscope_api.abort(f"Times must look like 09:00 (got '{t}').")
    return int(m.group(1)) * 60 + int(m.group(2))


OPEN, CLOSE = hm(open_t), hm(close_t)
if CLOSE <= OPEN:
    omniscope_api.abort("Closing time must be after opening time (overnight shifts are not supported).")
DAY = CLOSE - OPEN
WEEKMASK = {"SAT_SUN": "1111100", "FRI_SAT": "1111001", "SUN": "1111110", "NONE": "1111111"}[weekend]


def easter(y):
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = (h + l_ - 7 * m + 114) % 31 + 1
    return dt.date(y, month, day)


def nth_weekday(y, month, weekday, n):
    """n-th (1-based) weekday (Mon=0) of a month; n=-1 for the last."""
    if n > 0:
        d = dt.date(y, month, 1)
        d += dt.timedelta(days=(weekday - d.weekday()) % 7)
        return d + dt.timedelta(weeks=n - 1)
    d = dt.date(y + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def uk_substitutes(days):
    """Move holidays on a weekend to the next free weekday (UK rule)."""
    out, taken = [], set()
    for d, name in days:
        if d.weekday() >= 5:
            s = d
            while s.weekday() >= 5 or s in taken or any(s == x for x, _ in days if x != d):
                s += dt.timedelta(days=1)
            out.append((s, f"{name} (substitute day)"))
            taken.add(s)
        else:
            out.append((d, name))
            taken.add(d)
    return out


UK_ONE_OFF = {  # changes announced by the UK government (gov.uk/bank-holidays)
    2011: {"add": [(dt.date(2011, 4, 29), "Royal wedding")]},
    2012: {"move": {"Spring bank holiday": dt.date(2012, 6, 4)}, "add": [(dt.date(2012, 6, 5), "Queen's Diamond Jubilee")]},
    2020: {"move": {"Early May bank holiday": dt.date(2020, 5, 8)}},
    2022: {"move": {"Spring bank holiday": dt.date(2022, 6, 2)},
           "add": [(dt.date(2022, 6, 3), "Platinum Jubilee bank holiday"), (dt.date(2022, 9, 19), "State Funeral of Queen Elizabeth II")]},
    2023: {"add": [(dt.date(2023, 5, 8), "Coronation of King Charles III")]},
}


def uk_year(y, nation):
    e = easter(y)
    fixed = [(dt.date(y, 1, 1), "New Year's Day")]
    if nation == "SCOTLAND":
        fixed.append((dt.date(y, 1, 2), "2nd January"))
    if nation == "NI":
        fixed.append((dt.date(y, 3, 17), "St Patrick's Day"))
        fixed.append((dt.date(y, 7, 12), "Battle of the Boyne (Orangemen's Day)"))
    if nation == "SCOTLAND":
        fixed.append((dt.date(y, 11, 30), "St Andrew's Day"))
    fixed += [(dt.date(y, 12, 25), "Christmas Day"), (dt.date(y, 12, 26), "Boxing Day")]
    days = uk_substitutes(sorted(fixed))
    days.append((e - dt.timedelta(days=2), "Good Friday"))
    if nation != "SCOTLAND":
        days.append((e + dt.timedelta(days=1), "Easter Monday"))
    moved = UK_ONE_OFF.get(y, {}).get("move", {})
    early = moved.get("Early May bank holiday", nth_weekday(y, 5, 0, 1))
    spring = moved.get("Spring bank holiday", nth_weekday(y, 5, 0, -1))
    summer = nth_weekday(y, 8, 0, 1) if nation == "SCOTLAND" else nth_weekday(y, 8, 0, -1)
    days += [(early, "Early May bank holiday"), (spring, "Spring bank holiday"), (summer, "Summer bank holiday")]
    days += UK_ONE_OFF.get(y, {}).get("add", [])
    return days


def us_year(y):
    def observed(d, name):
        if d.weekday() == 5:
            return d - dt.timedelta(days=1), f"{name} (observed)"
        if d.weekday() == 6:
            return d + dt.timedelta(days=1), f"{name} (observed)"
        return d, name
    days = [observed(dt.date(y, 1, 1), "New Year's Day"),
            (nth_weekday(y, 1, 0, 3), "Martin Luther King Jr. Day"),
            (nth_weekday(y, 2, 0, 3), "Washington's Birthday"),
            (nth_weekday(y, 5, 0, -1), "Memorial Day")]
    if y >= 2021:
        days.append(observed(dt.date(y, 6, 19), "Juneteenth"))
    days += [observed(dt.date(y, 7, 4), "Independence Day"), (nth_weekday(y, 9, 0, 1), "Labor Day"),
             (nth_weekday(y, 10, 0, 2), "Columbus Day"), observed(dt.date(y, 11, 11), "Veterans Day"),
             (nth_weekday(y, 11, 3, 4), "Thanksgiving Day"), observed(dt.date(y, 12, 25), "Christmas Day")]
    return days


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


start = to_ts(df[start_f])
end = to_ts(df[end_f]) if end_f else pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
if as_of_txt:
    as_of = to_ts(pd.Series([as_of_txt], dtype=object)).iloc[0]
    if pd.isna(as_of):
        omniscope_api.abort("The 'as of' time must be a date and time, such as 2025-11-28 17:00.")
else:
    as_of = max(start.max(), end.max()) if start.notna().any() else pd.Timestamp.now().floor("min")
years = set(range((start.min().year if start.notna().any() else 2000) - 1, (max(as_of, end.max() if end.notna().any() else as_of)).year + 2))
hols = []
for y in years:
    if region != "NONE":
        days = us_year(y) if region == "US" else uk_year(y, {"ENGLAND_WALES": "EW", "SCOTLAND": "SCOTLAND", "NI": "NI"}[region])
        hols += [d0 for d0, _ in days]
for part in [p.strip() for p in (custom_holidays or "").replace(";", ",").split(",") if p.strip()]:
    v = pd.to_datetime(part, errors="coerce", dayfirst=not re.match(r"^\d{4}-", part))
    if pd.isna(v):
        omniscope_api.abort(f"Could not read the holiday date '{part}'.")
    hols.append(v.date())
HOL = np.array(sorted(set(hols)), dtype="datetime64[D]")


def is_work(d64):
    return np.is_busday(d64, weekmask=WEEKMASK, holidays=HOL)


def minutes_between(s, e):
    """Business minutes between timestamps (arrays of datetime64[ns]); NaN where missing or end before start."""
    s = s.astype("datetime64[m]")
    e = e.astype("datetime64[m]")
    bad = np.isnat(s) | np.isnat(e) | (e < s)
    s = np.where(bad, np.datetime64("2000-01-03T00:00", "m"), s)
    e = np.where(bad, np.datetime64("2000-01-03T00:00", "m"), e)
    ds, de = s.astype("datetime64[D]"), e.astype("datetime64[D]")
    ms = (s - ds.astype("datetime64[m]")).astype(int)
    me = (e - de.astype("datetime64[m]")).astype(int)
    ws, we = is_work(ds), is_work(de)
    same = ds == de
    first = np.where(ws, np.clip(CLOSE - np.clip(ms, OPEN, CLOSE), 0, DAY), 0)
    last = np.where(we, np.clip(np.clip(me, OPEN, CLOSE) - OPEN, 0, DAY), 0)
    middle = np.where(same, 0, np.busday_count(ds + np.timedelta64(1, "D"), de, weekmask=WEEKMASK, holidays=HOL)) * DAY
    within = np.where(ws, np.clip(np.clip(me, OPEN, CLOSE) - np.clip(ms, OPEN, CLOSE), 0, None), 0)
    out = np.where(same, within, first + middle + last).astype(float)
    out[bad] = np.nan
    return out


def add_minutes(s, mins):
    """The timestamp reached after `mins` business minutes from s."""
    if s is pd.NaT or pd.isna(s) or mins != mins:
        return pd.NaT
    t = pd.Timestamp(s).floor("min")
    rem = float(mins)
    d64 = np.datetime64(t.date())
    cur = t.hour * 60 + t.minute
    for _ in range(5000):
        if is_work(d64) and cur < CLOSE:
            startm = max(cur, OPEN)
            avail = CLOSE - startm
            if rem <= avail:
                return pd.Timestamp(d64) + pd.Timedelta(minutes=startm + rem)
            rem -= avail
        d64 = np.busday_offset(d64 + np.timedelta64(1, "D"), 0, roll="forward", weekmask=WEEKMASK, holidays=HOL)
        cur = OPEN
    return pd.NaT


# SLA targets
sla_map = {}
for part in [p.strip() for p in re.split(r"[,;\n]", sla_map_txt or "") if p.strip()]:
    m = re.match(r"^(.*?)\s*[=:]\s*([\d.]+)$", part)
    if not m:
        omniscope_api.abort(f"Could not read '{part}' in the SLA by priority list; use pairs such as P1=4, P2=8.")
    sla_map[m.group(1).strip().lower()] = float(m.group(2))
sla = np.full(len(df), np.nan)
if sla_f:
    sla = pd.to_numeric(df[sla_f], errors="coerce").astype("float64").to_numpy()
if prio_f and sla_map:
    pm = df[prio_f].astype(object).map(lambda v: sla_map.get(str(v).strip().lower(), np.nan) if v is not None and v == v else np.nan).to_numpy(dtype=float)
    sla = np.where(np.isnan(sla), pm, sla)
if sla_default > 0:
    sla = np.where(np.isnan(sla), sla_default, sla)

is_open = end.isna().to_numpy() & start.notna().to_numpy()
eff_end = end.where(end.notna(), as_of).to_numpy(dtype="datetime64[ns]")
bm = minutes_between(start.to_numpy(dtype="datetime64[ns]"), eff_end)
cal = (pd.Series(eff_end) - start.reset_index(drop=True)).dt.total_seconds().to_numpy() / 3600
due = [add_minutes(s_, h * 60) for s_, h in zip(start.tolist(), sla)]
out = df.copy()
out["Business Hours Elapsed"] = bm / 60
out["Calendar Hours Elapsed"] = np.where(np.isnan(bm), np.nan, cal)
out["Open"] = np.where(is_open, "Yes", np.where(start.notna().to_numpy(), "No", None))
out["SLA Hours"] = sla
out["SLA Due"] = pd.to_datetime(pd.Series(due, dtype="datetime64[ns]")).dt.tz_localize("UTC").to_numpy()
spare = sla - bm / 60
status = np.where(np.isnan(sla) | np.isnan(bm), None,
                  np.where(is_open, np.where(spare < 0, "Open and breached", "Open"), np.where(spare >= 0, "Met", "Breached")))
out["SLA Status"] = status
out["Business Hours To Spare"] = np.where(np.isnan(spare), np.nan, spare)
bad_rows = int(np.isnan(bm).sum())
for c in ("Business Hours Elapsed", "Calendar Hours Elapsed", "SLA Hours", "Business Hours To Spare"):
    out[c] = out[c].astype("float64")

grp = df[prio_f].astype(object).where(df[prio_f].notna(), "(blank)").map(str) if prio_f else pd.Series(["All"] * len(df))
srows = []
for g in sorted(set(grp)) + (["All"] if prio_f else []):
    m = (grp == g).to_numpy() if g != "All" or not prio_f else np.ones(len(df), dtype=bool)
    st = pd.Series(status[m])
    closed = st.isin(["Met", "Breached"])
    srows.append({"Priority": g, "Items": int(m.sum()), "Closed": int(closed.sum()), "Open": int(is_open[m].sum()), "Met": int((st == "Met").sum()),
                  "Breached": int((st == "Breached").sum()), "Open And Breached": int((st == "Open and breached").sum()),
                  "Met Rate (closed)": float((st == "Met").sum() / closed.sum()) if closed.sum() else np.nan,
                  "Median Business Hours": float(np.nanmedian(bm[m] / 60)) if np.isfinite(bm[m]).any() else np.nan,
                  "Median Calendar Hours": float(np.nanmedian(cal[m])) if np.isfinite(cal[m]).any() else np.nan})
summ = pd.DataFrame(srows)
for c in ("Items", "Closed", "Open", "Met", "Breached", "Open And Breached"):
    summ[c] = summ[c].astype("int64")
for c in ("Met Rate (closed)", "Median Business Hours", "Median Calendar Hours"):
    summ[c] = summ[c].astype("float64")
omniscope_api.write_output(out, "items")
omniscope_api.write_output(summ, "summary")
tot = summ.iloc[-1]
omniscope_api.close(f"{len(out):,} items, opening hours {open_t} to {close_t}: {int(tot['Met']):,} met, {int(tot['Breached']):,} breached, {int(tot['Open']):,} open"
                    + (f" ({int(tot['Open And Breached']):,} already breached)" if tot["Open And Breached"] else "")
                    + (f"; {bad_rows:,} rows without a valid start, or ending before they start, not measured" if bad_rows else "") + ".")
