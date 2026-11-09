"""Time Series Anomaly Detection: flag unusual days, weeks or months in one or
many series (per store, product, sensor, account) against a robust baseline.

  1. Optionally aggregate rows to day / week / month (sum, mean or count),
     filling empty periods with zero for sums and counts.
  2. Seasonal effect: for daily data, the typical difference of each weekday
     from the local level (median), so a quiet Sunday is not an anomaly.
  3. Baseline: rolling median of the de-seasonalised series (centred for
     reviewing history, or trailing to mimic live monitoring), and a robust
     spread: 1.4826 x rolling median absolute deviation (MAD).
  4. Score: robust z = (value - expected) / spread. |z| above the threshold
     (3.5 by default) is a spike or a dip; bounds are expected +- threshold x spread.

The median and MAD are not pulled about by the anomalies themselves, unlike a
mean and standard deviation.
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
series_fields = list(opt("series_fields", []) or [])
period = opt("period", "DAY")
agg = opt("aggregation", "SUM")
season = opt("seasonality", "AUTO")
window = int(opt("window", 28))
mode = opt("mode", "CENTRED")
thr = float(opt("threshold", 3.5))
direction = opt("direction", "BOTH")
min_hist = int(opt("min_history", 14))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the time series data to the input.")
if not date_f or date_f not in df.columns:
    omniscope_api.abort(f"Choose the date field (got '{date_f}').")
if agg != "COUNT" and (not value_f or value_f not in df.columns):
    omniscope_api.abort(f"Choose the value field (got '{value_f}'), or count rows.")
if value_f and value_f not in df.columns:
    omniscope_api.abort(f"Field '{value_f}' is not in the input.")
miss = [g for g in series_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Series fields not in the input: {', '.join(miss)}")
if window < 5:
    omniscope_api.abort("The window must be at least 5 periods.")
if thr <= 0:
    omniscope_api.abort("The threshold must be above zero.")


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
    return d.astype("datetime64[ns]")


FREQ = {"DAY": "D", "WEEK": "W-SUN", "MONTH": "M"}  # W-SUN = weeks ending Sunday, so periods start on Monday
w = pd.DataFrame({"t": to_date(df[date_f]), "v": pd.to_numeric(df[value_f], errors="coerce").astype("float64") if value_f else 1.0})
for g in series_fields:
    w[g] = df[g].astype(object).where(df[g].notna(), "(blank)").map(str)
bad = int(w["t"].isna().sum())
w = w.dropna(subset=["t"])
if period != "NONE":
    w["p"] = w["t"].dt.to_period(FREQ[period]).dt.start_time
else:
    w["p"] = w["t"]


def scale_of(x):
    """1.4826 x MAD, falling back to the mean absolute deviation, then to a tiny positive number."""
    med = np.nanmedian(x)
    mad = np.nanmedian(np.abs(x - med))
    if mad > 0:
        return 1.4826 * mad
    mean_ad = np.nanmean(np.abs(x - med))
    return 1.2533 * mean_ad if mean_ad > 0 else 0.0


out_parts = []
keys = [((), w)] if not series_fields else [((k if isinstance(k, tuple) else (k,)), g) for k, g in w.groupby(series_fields, sort=True)]
for key, g in keys:
    if agg == "SUM":
        s = g.groupby("p")["v"].sum(min_count=1)
    elif agg == "MEAN":
        s = g.groupby("p")["v"].mean()
    elif agg == "COUNT":
        s = g.groupby("p")["v"].size().astype(float)
    else:  # NONE: one value per period expected; take the last
        s = g.sort_values("t").groupby("p")["v"].last()
    if period != "NONE" and len(s):
        full = pd.period_range(s.index.min(), s.index.max(), freq=FREQ[period]).start_time
        filled = s.reindex(full)
        if agg in ("SUM", "COUNT"):
            filled = filled.fillna(0.0)
        s = filled
    s = s.sort_index()
    v = s.to_numpy(dtype=float)
    n = len(v)
    # seasonal (weekday) effect for daily data
    use_season = period == "DAY" and season in ("AUTO", "WEEKLY") and n >= 21
    level0 = pd.Series(v).rolling(7 if use_season else max(3, window // 4), center=True, min_periods=1).median().to_numpy()
    seas = np.zeros(n)
    if use_season:
        dow = pd.DatetimeIndex(s.index).dayofweek
        dev = pd.Series(v - level0).groupby(dow).median()
        if season == "AUTO":
            spread_all = scale_of(v - level0)
            if not (spread_all > 0 and (dev.abs().max() > 0.5 * spread_all)):
                dev[:] = 0.0  # no clear weekday pattern
        seas = dev.reindex(dow).to_numpy(dtype=float)
        seas = np.nan_to_num(seas)
    ds = pd.Series(v - seas)
    if mode == "TRAILING":
        roll = ds.shift(1).rolling(window, min_periods=min_hist)
    else:
        roll = ds.rolling(window, center=True, min_periods=min(min_hist, window))
    base = roll.median().to_numpy()
    spread = roll.apply(scale_of, raw=True).to_numpy()
    expected = base + seas
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where((spread > 0) & ~np.isnan(v), (v - expected) / spread, np.where(np.isnan(v) | np.isnan(base), np.nan, 0.0))
    z = np.where(np.isnan(base), np.nan, z)
    flag = np.full(n, "No", dtype=object)
    if direction in ("BOTH", "UP"):
        flag[z > thr] = "Spike"
    if direction in ("BOTH", "DOWN"):
        flag[z < -thr] = "Dip"
    flag[np.isnan(z)] = "Not scored"
    part = pd.DataFrame({"Period": s.index, "Value": v, "Expected": expected, "Lower Bound": expected - thr * spread, "Upper Bound": expected + thr * spread,
                         "Weekday Effect": seas, "Robust Z": z, "Anomaly": flag})
    for i, gname in enumerate(series_fields):
        part.insert(i, gname, key[i])
    out_parts.append(part)

cols = series_fields + ["Period", "Value", "Expected", "Lower Bound", "Upper Bound", "Weekday Effect", "Robust Z", "Anomaly"]
res = pd.concat(out_parts, ignore_index=True) if out_parts else pd.DataFrame(columns=cols)
res["Period"] = pd.to_datetime(res["Period"]).dt.tz_localize("UTC") if len(res) else pd.Series([], dtype="datetime64[ns, UTC]")
for c in ("Value", "Expected", "Lower Bound", "Upper Bound", "Weekday Effect", "Robust Z"):
    res[c] = res[c].astype("float64")
res["Deviation"] = (res["Value"] - res["Expected"]).astype("float64")
res["Deviation %"] = np.where(res["Expected"].abs() > 0, res["Deviation"] / res["Expected"].abs(), np.nan).astype("float64")

an = res[res["Anomaly"].isin(["Spike", "Dip"])].copy()
an["Severity"] = an["Robust Z"].abs()
an = an.sort_values("Severity", ascending=False, kind="mergesort").reset_index(drop=True)
an = an[series_fields + ["Period", "Anomaly", "Value", "Expected", "Deviation", "Deviation %", "Robust Z", "Severity"]]

srows = []
for key, g in (res.groupby(series_fields, sort=True) if series_fields else [((), res)]):
    key = key if isinstance(key, tuple) else (key,)
    last = g.iloc[-1] if len(g) else None
    srows.append({**dict(zip(series_fields, key)), "Periods": len(g), "Scored": int((g["Anomaly"] != "Not scored").sum()),
                  "Spikes": int((g["Anomaly"] == "Spike").sum()), "Dips": int((g["Anomaly"] == "Dip").sum()),
                  "Latest Period": last["Period"] if last is not None else pd.NaT, "Latest Value": float(last["Value"]) if last is not None else np.nan,
                  "Latest Status": last["Anomaly"] if last is not None else None,
                  "Largest Spike Z": float(g["Robust Z"].max()) if g["Robust Z"].notna().any() else np.nan,
                  "Largest Dip Z": float(g["Robust Z"].min()) if g["Robust Z"].notna().any() else np.nan})
summ = pd.DataFrame(srows, columns=series_fields + ["Periods", "Scored", "Spikes", "Dips", "Latest Period", "Latest Value", "Latest Status", "Largest Spike Z", "Largest Dip Z"])
for c in ("Periods", "Scored", "Spikes", "Dips"):
    summ[c] = summ[c].astype("int64")
for c in ("Latest Value", "Largest Spike Z", "Largest Dip Z"):
    summ[c] = summ[c].astype("float64")
summ["Latest Period"] = pd.to_datetime(summ["Latest Period"], utc=True)

omniscope_api.write_output(res, "series")
omniscope_api.write_output(an, "anomalies")
omniscope_api.write_output(summ, "summary")
omniscope_api.close(f"{len(keys):,} series, {len(res):,} periods scored; {int((res['Anomaly'] == 'Spike').sum()):,} spikes and {int((res['Anomaly'] == 'Dip').sum()):,} dips "
                    f"at |z| > {thr:g} ({mode.lower()} window of {window})" + (f"; {bad:,} rows without a valid date skipped" if bad else "") + ".")
