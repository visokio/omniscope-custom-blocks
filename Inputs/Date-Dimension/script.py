"""Date Dimension: a calendar table with one row per day, for joining to any
fact table and for report filters:

  calendar year, quarter, month, week (ISO), day names and numbers,
  fiscal year, quarter and month for a fiscal year starting in any month,
  weekends, public holidays (England and Wales, Scotland, Northern Ireland,
  US federal, or none) plus your own dates, working-day flags and counts
  (n-th working day of the month, working days in and left in the month),
  month, quarter and year start / end flags, and optional days, months and
  years relative to a reference date.

The range comes from the start and end options, or from the dates in a field
of the optional input (whole years by default).
"""
import datetime as dt

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


start_txt = opt("start_date", "")
end_txt = opt("end_date", "")
date_f = opt("date_field")
whole_years = bool(opt("whole_years", True))
fy_start = int(opt("fiscal_year_start", 1))
fy_label = opt("fiscal_label", "END_YEAR")
region = opt("region", "ENGLAND_WALES")
custom_holidays = opt("custom_holidays", "")
weekend = opt("weekend", "SAT_SUN")
ref_txt = opt("reference_date", "")

df = omniscope_api.read_input_records(input_number=0)
if not 1 <= fy_start <= 12:
    omniscope_api.abort("Fiscal year start month must be 1 to 12.")


def parse_one(t):
    t = str(t).strip()
    if t.upper() == "TODAY":
        return pd.Timestamp(dt.date.today())
    iso = len(t) >= 8 and t[:4].isdigit() and t[4] == "-"
    v = pd.to_datetime(t, errors="coerce", dayfirst=not iso)
    if pd.isna(v):
        omniscope_api.abort(f"Could not read the date '{t}'. Use a date such as 2025-01-31.")
    return pd.Timestamp(v).tz_localize(None).normalize() if getattr(v, "tzinfo", None) else pd.Timestamp(v).normalize()


if date_f and df is not None:
    if date_f not in df.columns:
        omniscope_api.abort(f"Field '{date_f}' is not in the input.")
    s = df[date_f]
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s.dt.tz_localize(None) if s.dt.tz is not None else s
    else:
        txt = s.astype(object).where(s.notna(), None).astype(str).str.strip()
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        d = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        d[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
        d[~iso & s.notna()] = pd.to_datetime(txt[~iso & s.notna()], errors="coerce", dayfirst=True, format="mixed")
    d = d.dropna()
    if d.empty:
        omniscope_api.abort(f"Field '{date_f}' has no valid dates.")
    start, end = d.min().normalize(), d.max().normalize()
    if start_txt:
        start = parse_one(start_txt)
    if end_txt:
        end = parse_one(end_txt)
    if whole_years and not start_txt and not end_txt:
        start, end = pd.Timestamp(start.year, 1, 1), pd.Timestamp(end.year, 12, 31)
else:
    if not start_txt or not end_txt:
        omniscope_api.abort("Give a start and end date, or connect data and choose its date field.")
    start, end = parse_one(start_txt), parse_one(end_txt)
if end < start:
    omniscope_api.abort(f"The end date {end.date()} is before the start date {start.date()}.")
if (end - start).days > 366 * 200:
    omniscope_api.abort("The range is more than 200 years; choose a shorter range.")


# ------------------------------------------------------------- holidays (same rules as the Working Days block)
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


def holidays_for(years):
    rows = []
    for y in years:
        if region == "NONE":
            continue
        days = us_year(y) if region == "US" else uk_year(y, {"ENGLAND_WALES": "EW", "SCOTLAND": "SCOTLAND", "NI": "NI"}[region])
        rows += [(d, n) for d, n in days]
    for part in [p.strip() for p in (custom_holidays or "").replace(";", ",").replace("\n", ",").split(",") if p.strip()]:
        bits = part.split("=", 1) if "=" in part else part.split(" ", 1)
        when = parse_one(bits[0]).date()
        if when.year in years:
            rows.append((when, bits[1].strip() if len(bits) > 1 and bits[1].strip() else "Custom holiday"))
    return rows


dates = pd.date_range(start, end, freq="D")
years = set(range(start.year, end.year + 1))
hol = {}
for d0, name in holidays_for(years):
    k = pd.Timestamp(d0)
    hol[k] = name if k not in hol else hol[k] + "; " + name
WEEKEND = {"SAT_SUN": (5, 6), "FRI_SAT": (4, 5), "SUN": (6,), "NONE": ()}[weekend]

c = pd.DataFrame({"Date": dates})
dtd = c["Date"].dt
c["Year"] = dtd.year.astype("int64")
c["Quarter"] = dtd.quarter.astype("int64")
c["Quarter Name"] = "Q" + c["Quarter"].astype(str)
c["Year Quarter"] = c["Year"].astype(str) + "-Q" + c["Quarter"].astype(str)
c["Month"] = dtd.month.astype("int64")
c["Month Name"] = dtd.strftime("%B")
c["Month Short"] = dtd.strftime("%b")
c["Year Month"] = dtd.strftime("%Y-%m")
c["Day Of Month"] = dtd.day.astype("int64")
c["Day Of Year"] = dtd.dayofyear.astype("int64")
c["Day Of Week"] = (dtd.dayofweek + 1).astype("int64")
c["Day Name"] = dtd.strftime("%A")
c["Day Short"] = dtd.strftime("%a")
iso = dtd.isocalendar()
c["ISO Year"] = iso["year"].astype("int64").to_numpy()
c["ISO Week"] = iso["week"].astype("int64").to_numpy()
c["ISO Year Week"] = c["ISO Year"].astype(str) + "-W" + c["ISO Week"].astype(str).str.zfill(2)
c["Week Start (Monday)"] = c["Date"] - pd.to_timedelta(dtd.dayofweek, unit="D")
c["Days In Month"] = dtd.days_in_month.astype("int64")
c["Month Start"] = c["Date"].values.astype("datetime64[M]").astype("datetime64[ns]")
c["Month End"] = c["Month Start"] + pd.to_timedelta(c["Days In Month"] - 1, unit="D")
c["Is Month Start"] = np.where(c["Day Of Month"] == 1, "Yes", "No")
c["Is Month End"] = np.where(c["Date"] == c["Month End"], "Yes", "No")
c["Is Quarter End"] = np.where((c["Is Month End"] == "Yes") & (c["Month"] % 3 == 0), "Yes", "No")
c["Is Year End"] = np.where((c["Month"] == 12) & (c["Day Of Month"] == 31), "Yes", "No")
c["Is Leap Year"] = np.where(dtd.is_leap_year, "Yes", "No")

# fiscal: a year starting in month fy_start; by default named after the calendar year it ends in (FY2026 = Apr 2025 to Mar 2026)
yr, mo = c["Year"].to_numpy(), c["Month"].to_numpy()
if fy_start == 1:
    fy_first, fy_last = yr, yr
else:
    fy_first = np.where(mo >= fy_start, yr, yr - 1)
    fy_last = fy_first + 1
fm = ((c["Month"] - fy_start) % 12 + 1).astype("int64")
c["Fiscal Year"] = (fy_first if fy_label == "START_YEAR" else fy_last).astype("int64")
if fy_label == "SPAN" and fy_start != 1:
    c["Fiscal Year Name"] = "FY " + pd.Series(fy_first).astype(str) + "/" + pd.Series(fy_last % 100).astype(str).str.zfill(2)
else:
    c["Fiscal Year Name"] = "FY" + c["Fiscal Year"].astype(str)
c["Fiscal Month"] = fm
c["Fiscal Quarter"] = ((fm - 1) // 3 + 1).astype("int64")
c["Fiscal Year Quarter"] = c["Fiscal Year Name"] + " Q" + c["Fiscal Quarter"].astype(str)
c["Fiscal Year Month"] = c["Fiscal Year Name"] + " P" + c["Fiscal Month"].astype(str).str.zfill(2)
fys = pd.to_datetime(pd.DataFrame({"year": fy_first, "month": fy_start, "day": 1}))
c["Fiscal Year Start"] = fys
c["Fiscal Day Of Year"] = ((c["Date"] - fys).dt.days + 1).astype("int64")

# weekends, holidays, working days
is_we = dtd.dayofweek.isin(WEEKEND)
hn = c["Date"].map(hol)
c["Is Weekend"] = np.where(is_we, "Yes", "No")
c["Is Holiday"] = np.where(hn.notna(), "Yes", "No")
c["Holiday Name"] = hn.astype(object).where(hn.notna(), None)
work = (~is_we & hn.isna()).to_numpy()
c["Is Working Day"] = np.where(work, "Yes", "No")
wk = pd.Series(work.astype(int))
grp = c["Year Month"]
c["Working Day Of Month"] = pd.array(np.where(work, wk.groupby(grp).cumsum(), np.nan), dtype="Float64").astype("Int64")
c["Working Days In Month"] = wk.groupby(grp).transform("sum").astype("int64")
c["Working Days Left In Month"] = (c["Working Days In Month"] - wk.groupby(grp).cumsum()).astype("int64")
last_wd = c[work].groupby("Year Month")["Date"].max()
c["Is Last Working Day Of Month"] = np.where(c["Date"].isin(set(last_wd)), "Yes", "No")
c["Working Days Since Start"] = wk.cumsum().astype("int64")
wd_dates = pd.Series(np.where(work, c["Date"], pd.NaT), dtype="datetime64[ns]")
c["Next Working Day"] = wd_dates.bfill().to_numpy()       # this day if it is a working day, else the next one (blank after the last)
c["Previous Working Day"] = wd_dates.ffill().to_numpy()   # this day if it is a working day, else the one before

if ref_txt:
    ref = parse_one(ref_txt)
    c["Days From Reference"] = (c["Date"] - ref).dt.days.astype("int64")
    c["Months From Reference"] = ((c["Year"] - ref.year) * 12 + (c["Month"] - ref.month)).astype("int64")
    c["Years From Reference"] = (c["Year"] - ref.year).astype("int64")
    c["Is Past"] = np.where(c["Date"] < ref, "Yes", "No")

for col in ("Date", "Week Start (Monday)", "Month Start", "Month End", "Fiscal Year Start", "Next Working Day", "Previous Working Day"):
    c[col] = pd.to_datetime(c[col]).dt.tz_localize("UTC")

hl = pd.DataFrame([(pd.Timestamp(d0), n) for d0, n in holidays_for(years)], columns=["Date", "Holiday Name"])
hl["Date"] = pd.to_datetime(hl["Date"]).astype("datetime64[ns]")
hl = hl[(hl["Date"] >= start) & (hl["Date"] <= end)].sort_values("Date").reset_index(drop=True)
hl["Day Name"] = hl["Date"].dt.strftime("%A")
hl["Year"] = hl["Date"].dt.year.astype("int64")
hl["Date"] = pd.to_datetime(hl["Date"]).dt.tz_localize("UTC")

omniscope_api.write_output(c, "calendar")
omniscope_api.write_output(hl, "holidays")
omniscope_api.close(f"{len(c):,} days from {start.date()} to {end.date()}; {int(work.sum()):,} working days, {len(hl):,} holidays"
                    + (f" ({ {'ENGLAND_WALES': 'England and Wales', 'SCOTLAND': 'Scotland', 'NI': 'Northern Ireland', 'US': 'US federal'}[region]})" if region != "NONE" else "") + f"; fiscal year starts in month {fy_start}.")
