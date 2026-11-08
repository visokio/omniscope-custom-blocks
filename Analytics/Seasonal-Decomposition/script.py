"""Seasonal Decomposition: split each time series into trend, seasonal and
residual components (classical decomposition with a centred moving average),
additive or multiplicative, with seasonally adjusted values, seasonal indices
per season (for example per month) and a summary of how strong the trend and
seasonality are.

One row per period is built per series: duplicate dates in a period are
summed and missing periods interpolated (and flagged).
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


date_field = opt("date_field")
value_field = opt("value_field")
group_fields = opt("group_fields", []) or []
frequency = opt("frequency", "MONTH")
season_len = int(opt("season_length", 0) or 0)
model = opt("model", "ADDITIVE")
extend = opt("extend_trend", True)
FREQ = {"DAY": ("D", 7), "WEEK": ("W-SUN", 52), "MONTH": ("M", 12), "QUARTER": ("Q-DEC", 4)}

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the time series to the input.")
for f, label in ((date_field, "date"), (value_field, "value")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
miss = [g for g in group_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Series fields not in the input: {', '.join(miss)}")
freq, default_m = FREQ.get(frequency, ("M", 12))
m = season_len or default_m
if m < 2:
    omniscope_api.abort("Season length must be at least 2.")

d = df[date_field]
if pd.api.types.is_datetime64_any_dtype(d):
    dates = d.dt.tz_localize(None) if d.dt.tz is not None else d
else:
    txt = d.astype(object).where(d.notna(), None).astype(str).str.strip()
    iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
    dates = pd.Series(pd.NaT, index=d.index, dtype="datetime64[ns]")
    dates[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
    dates[~iso & d.notna()] = pd.to_datetime(txt[~iso & d.notna()], errors="coerce", dayfirst=True, format="mixed")
w = pd.DataFrame({"p": dates.dt.to_period(freq), "y": pd.to_numeric(df[value_field], errors="coerce")})
for g in group_fields:
    w[g] = df[g].astype(object).where(df[g].notna(), "(blank)")
w = w.dropna(subset=["p", "y"])

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def season_label(p):
    if frequency == "MONTH" and m == 12:
        return MONTHS[p.month - 1]
    if frequency == "QUARTER" and m == 4:
        return f"Q{p.quarter}"
    if frequency == "DAY" and m == 7:
        return DAYS[p.dayofweek]
    if frequency == "WEEK" and m == 52:
        return f"Week {min(p.week, 52)}"
    return None


def season_pos(p):
    if frequency == "MONTH" and m == 12:
        return p.month - 1
    if frequency == "QUARTER" and m == 4:
        return p.quarter - 1
    if frequency == "DAY" and m == 7:
        return p.dayofweek
    if frequency == "WEEK" and m == 52:
        return min(p.week, 52) - 1
    return p.ordinal % m


def centred_ma(y, m):
    if m % 2 == 1:
        k = np.ones(m) / m
    else:
        k = np.r_[0.5, np.ones(m - 1), 0.5] / m
    h = len(k) // 2
    t = np.full(len(y), np.nan)
    if len(y) >= len(k):
        t[h:len(y) - h] = np.convolve(y, k, mode="valid")
    return t


groups = [((), w)] if not group_fields else [((k if isinstance(k, tuple) else (k,)), g) for k, g in w.groupby(group_fields, sort=True)]
series_out, index_out, summ_out = [], [], []
mult = model == "MULTIPLICATIVE"
for key, g in groups:
    gd = {c: key[i] for i, c in enumerate(group_fields)}
    s = g.groupby("p")["y"].sum().sort_index()
    if s.empty:
        continue
    full = pd.period_range(s.index.min(), s.index.max(), freq=freq)
    s = s.reindex(full)
    interp = s.isna().to_numpy()
    s = s.interpolate(limit_direction="both")
    y = s.to_numpy(dtype=float)
    n = len(y)
    pos = np.array([season_pos(p) for p in full])
    if n < 2 * m or (mult and (y <= 0).any()):
        reason = (f"Needs at least two full seasons ({2 * m} periods); has {n}." if n < 2 * m
                  else "Multiplicative model needs all values above zero.")
        summ_out.append({**gd, "Model": model.title(), "Season Length": m, "Periods": n, "Status": reason})
        continue
    trend = centred_ma(y, m)
    if extend:
        ok = np.flatnonzero(~np.isnan(trend))
        for side in ("start", "end"):
            sel = ok[:m] if side == "start" else ok[-m:]
            b, a = np.polyfit(sel, trend[sel], 1)
            rng = np.arange(0, ok[0]) if side == "start" else np.arange(ok[-1] + 1, n)
            trend[rng] = a + b * rng
    detr = y / trend if mult else y - trend
    idx = np.full(m, np.nan)
    for k in range(m):
        vals = detr[(pos == k) & ~np.isnan(detr)]
        idx[k] = vals.mean() if len(vals) else (1.0 if mult else 0.0)
    idx = idx / idx.mean() if mult else idx - idx.mean()
    seas = idx[pos]
    resid = y / (trend * seas) if mult else y - trend - seas
    adj = y / seas if mult else y - seas
    # strength measures (Wang, Smith and Hyndman), on the additive scale
    if mult:
        R, S, T = np.log(resid), np.log(seas), np.log(trend)
    else:
        R, S, T = resid, seas, trend
    okr = ~np.isnan(R) & ~np.isnan(T)
    fs = max(0.0, 1 - np.var(R[okr]) / np.var((S + R)[okr])) if okr.sum() > 2 and np.var((S + R)[okr]) > 0 else np.nan
    ft = max(0.0, 1 - np.var(R[okr]) / np.var((T + R)[okr])) if okr.sum() > 2 and np.var((T + R)[okr]) > 0 else np.nan
    labels = [season_label(p) for p in full]
    for i, p in enumerate(full):
        series_out.append({**gd, "Period": str(p), "Period Start": p.start_time, "Season": labels[i] or f"Season {pos[i] + 1}",
                           "Value": y[i], "Trend": trend[i], "Seasonal": seas[i], "Residual": resid[i],
                           "Seasonally Adjusted": adj[i], "Is Interpolated": "Yes" if interp[i] else "No"})
    first_lab = {}
    for i, p in enumerate(full):
        first_lab.setdefault(pos[i], labels[i] or f"Season {pos[i] + 1}")
    for k in range(m):
        index_out.append({**gd, "Season Number": k + 1, "Season": first_lab.get(k, f"Season {k + 1}"), "Seasonal Index": idx[k],
                          "Effect": (f"{(idx[k] - 1):+.1%} vs trend" if mult else f"{idx[k]:+,.4g} vs trend")})
    peak, trough = int(np.nanargmax(idx)), int(np.nanargmin(idx))
    tr = trend[~np.isnan(trend)]
    summ_out.append({**gd, "Model": model.title(), "Season Length": m, "Periods": n, "Status": "OK",
                     "Seasonality Strength": fs, "Trend Strength": ft,
                     "Peak Season": first_lab.get(peak, str(peak + 1)), "Trough Season": first_lab.get(trough, str(trough + 1)),
                     "Trend Change": (tr[-1] / tr[0] - 1) if len(tr) and tr[0] else np.nan,
                     "Residual Std Dev": float(np.nanstd(resid)), "Interpolated Periods": int(interp.sum())})

scols = list(group_fields) + ["Period", "Period Start", "Season", "Value", "Trend", "Seasonal", "Residual", "Seasonally Adjusted", "Is Interpolated"]
so = pd.DataFrame(series_out, columns=scols)
so["Period Start"] = pd.to_datetime(so["Period Start"]).dt.tz_localize("UTC")
for c in ("Value", "Trend", "Seasonal", "Residual", "Seasonally Adjusted"):
    so[c] = so[c].astype("float64")
io = pd.DataFrame(index_out, columns=list(group_fields) + ["Season Number", "Season", "Seasonal Index", "Effect"])
io["Season Number"] = io["Season Number"].astype("int64")
io["Seasonal Index"] = io["Seasonal Index"].astype("float64")
mcols = list(group_fields) + ["Model", "Season Length", "Periods", "Status", "Seasonality Strength", "Trend Strength", "Peak Season",
                              "Trough Season", "Trend Change", "Residual Std Dev", "Interpolated Periods"]
mo = pd.DataFrame(summ_out, columns=mcols)
for c in ("Season Length", "Periods"):
    mo[c] = mo[c].astype("int64")
mo["Interpolated Periods"] = pd.array(mo["Interpolated Periods"].to_numpy(dtype=float), dtype="Float64").astype("Int64")
for c in ("Seasonality Strength", "Trend Strength", "Trend Change", "Residual Std Dev"):
    mo[c] = mo[c].astype("float64")

omniscope_api.write_output(so, "components")
omniscope_api.write_output(io, "indices")
omniscope_api.write_output(mo, "summary")
okn = int((mo["Status"] == "OK").sum())
omniscope_api.close(f"{okn} of {len(mo)} series decomposed ({model.lower()}, season length {m}).")
