"""Age and Tenure: exact age or length of service between a start date (date
of birth, joining date, contract start) and an as-of date, in completed years,
months and days, with decimal years, a band (for example 18-24, 25-34...), the
next anniversary and the days until it, and a milestone flag (5, 10, 25 years).

Completed years follow the calendar: someone born on 29 February has their
birthday on 28 February in non-leap years. An end date field (for example a
leaving date) is used as the as-of date where it is filled; rows that ended
before the as-of date (leavers) get no upcoming milestone.
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
as_of_txt = opt("as_of", "")
bands_txt = opt("bands", "18, 25, 35, 45, 55, 65")
miles_txt = opt("milestones", "5, 10, 15, 20, 25, 30, 40")
prefix = opt("prefix", "")
window = int(opt("milestone_window_days", 90))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
if not start_f or start_f not in df.columns:
    omniscope_api.abort(f"Choose the start date field (got '{start_f}').")
if end_f and end_f not in df.columns:
    omniscope_api.abort(f"Field '{end_f}' is not in the input.")
try:
    bands = sorted({int(x) for x in re.split(r"[,;\s]+", bands_txt) if x.strip()})
    miles = sorted({int(x) for x in re.split(r"[,;\s]+", miles_txt) if x.strip()})
except ValueError:
    omniscope_api.abort("Bands and milestones must be whole numbers of years, for example: 18, 25, 35")


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
    return d.astype("datetime64[ns]").dt.normalize()


st = to_date(df[start_f])
if as_of_txt:
    as_of = to_date(pd.Series([as_of_txt], dtype=object)).iloc[0]
    if pd.isna(as_of):
        omniscope_api.abort("The as-of date must be a date, such as 2025-11-05.")
else:
    as_of = pd.Timestamp.today().normalize()
en = to_date(df[end_f]).where(lambda s: s.notna(), as_of) if end_f else pd.Series(as_of, index=df.index)


def anniv(d, y):
    """d's anniversary in year y (29 February falls on 28 February in non-leap years)."""
    try:
        return pd.Timestamp(year=y, month=d.month, day=d.day)
    except ValueError:
        return pd.Timestamp(year=y, month=2, day=28)


def span(a, b):
    """Label of the band from a up to (not including) b: "1" when it covers a single year."""
    return f"{a}" if b - a == 1 else f"{a}-{b - 1}"


Y, M, D, DEC, NEXT, DAYS, BAND, MILE = [], [], [], [], [], [], [], []
for s, e in zip(st, en):
    if pd.isna(s) or pd.isna(e) or e < s:
        for lst in (Y, M, D, DEC, DAYS):
            lst.append(np.nan)
        NEXT.append(pd.NaT); BAND.append(None); MILE.append(None)
        continue
    years = e.year - s.year - (1 if anniv(s, e.year) > e else 0)
    last = anniv(s, s.year + years)
    months = 0
    while True:
        cand = last + pd.DateOffset(months=months + 1)
        if cand <= e:
            months += 1
        else:
            break
    days = (e - (last + pd.DateOffset(months=months))).days
    nxt = anniv(s, s.year + years + 1)
    Y.append(years); M.append(months); D.append(days)
    DEC.append(years + (e - last).days / (nxt - last).days)
    NEXT.append(nxt); DAYS.append((nxt - e).days)
    lo = [b for b in bands if b <= years]
    hi = [b for b in bands if b > years]
    BAND.append((f"Under {bands[0]}" if not lo else span(lo[-1], hi[0]) if hi else f"{bands[-1]}+") if bands else None)
    # Upcoming milestones are for current staff only, counted from the as-of date: a row whose end date is
    # before the as-of date has left; one with a later end date gets a milestone only if it falls before that date.
    m = None
    if e >= as_of:
        ya = as_of.year - s.year - (1 if anniv(s, as_of.year) > as_of else 0)
        na = anniv(s, s.year + ya + 1)
        if ya + 1 in miles and (na - as_of).days <= window and (e == as_of or na <= e):
            m = f"{ya + 1} years on {na.date()}"
    MILE.append(m)
out = df.copy()
out[f"{prefix}Years"] = pd.array(np.array(Y, dtype=float), dtype="Float64").astype("Int64")
out[f"{prefix}Months"] = pd.array(np.array(M, dtype=float), dtype="Float64").astype("Int64")
out[f"{prefix}Days"] = pd.array(np.array(D, dtype=float), dtype="Float64").astype("Int64")
out[f"{prefix}Decimal Years"] = np.array(DEC, dtype=float)
out[f"{prefix}Band"] = BAND
out[f"{prefix}Next Anniversary"] = pd.to_datetime(pd.Series(NEXT, dtype="datetime64[ns]")).dt.tz_localize("UTC").to_numpy()
out[f"{prefix}Days To Next Anniversary"] = pd.array(np.array(DAYS, dtype=float), dtype="Float64").astype("Int64")
out[f"{prefix}Upcoming Milestone"] = MILE
omniscope_api.write_output(out, "rows")
bc = pd.Series(BAND).value_counts()
summ = pd.DataFrame({"Band": bc.index, "Rows": bc.to_numpy().astype("int64")})
order = {b: i for i, b in enumerate([f"Under {bands[0]}"] + [span(a, b) for a, b in zip(bands[:-1], bands[1:])] + [f"{bands[-1]}+"])} if bands else {}
summ = summ.sort_values("Band", key=lambda s: s.map(order), kind="mergesort").reset_index(drop=True)
summ["Share"] = (summ["Rows"] / max(1, summ["Rows"].sum())).astype("float64")
omniscope_api.write_output(summ, "bands")
bad = int(pd.isna(pd.Series(Y, dtype=float)).sum())
omniscope_api.close(f"{len(out) - bad:,} of {len(out):,} rows measured as of {as_of.date()}; {sum(1 for x in MILE if x):,} milestones within {window} days"
                    + (f"; {bad:,} rows without a valid start (or ending before it)" if bad else "") + ".")
