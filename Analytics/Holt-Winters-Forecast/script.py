"""Holt-Winters Forecast: exponential smoothing forecasts per series (product,
store, region, cost centre), with trend and seasonality.

  Models: level only, additive trend or damped trend, combined with no,
  additive or multiplicative seasonality (the Holt-Winters / ETS family).
  Smoothing parameters are fitted by least squares (scipy); with Automatic,
  the model with the lowest AICc is chosen per series.
  Prediction intervals (80% and 95%) come from simulating future paths with
  the model's own resampled one-step errors, so they widen with the horizon
  and suit every model type.
  Optional holdout: the last N periods are forecast from the earlier data and
  scored (MAE, RMSE, MAPE) against a seasonal naive forecast (MASE below 1
  means the model beats "same as last season").

Rows are aggregated to day, week, month or quarter first; empty periods count
as zero.
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi
from scipy.optimize import minimize

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


date_f = opt("date_field")
value_f = opt("value_field")
series_fields = list(opt("series_fields", []) or [])
period = opt("period", "MONTH")
horizon = int(opt("horizon", 12))
season_len = int(opt("season_length", 0) or 0)
trend_opt = opt("trend", "AUTO")
season_opt = opt("seasonality", "AUTO")
holdout = int(opt("holdout", 0) or 0)
sims = int(opt("simulations", 1000))
seed = int(opt("seed", 1))
FREQ = {"DAY": "D", "WEEK": "W-SUN", "MONTH": "M", "QUARTER": "Q-DEC"}
M_DEFAULT = {"DAY": 7, "WEEK": 52, "MONTH": 12, "QUARTER": 4}

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the history to the input.")
for f, lab in ((date_f, "date"), (value_f, "value")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
miss = [g for g in series_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Series fields not in the input: {', '.join(miss)}")
if not 1 <= horizon <= 1000:
    omniscope_api.abort("Horizon must be 1 to 1000 periods.")
m = season_len or M_DEFAULT[period]


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


def run_hw(y, a, b, g, phi, trend, season, m, init):
    """One-step-ahead fitted values and final states."""
    l, bt, s = init
    s = list(s)
    n = len(y)
    fit = np.empty(n)
    for t in range(n):
        sv = s[t % m] if season != "N" else (1.0 if season == "M" else 0.0)
        damp = phi * bt if trend != "N" else 0.0
        base = l + damp
        yhat = base * sv if season == "M" else base + sv
        fit[t] = yhat
        yt = y[t]
        if season == "M":
            l_new = a * (yt / sv) + (1 - a) * base
        elif season == "A":
            l_new = a * (yt - sv) + (1 - a) * base
        else:
            l_new = a * yt + (1 - a) * base
        if trend != "N":
            bt = b * (l_new - l) + (1 - b) * damp
        if season == "M":
            s[t % m] = g * (yt / l_new) + (1 - g) * sv if l_new != 0 else sv
        elif season == "A":
            s[t % m] = g * (yt - l_new) + (1 - g) * sv
        l = l_new
    return fit, (l, bt, s, n)


def initial(y, trend, season, m):
    if season != "N":
        l0 = y[:m].mean()
        b0 = (y[m:2 * m].mean() - y[:m].mean()) / m if trend != "N" and len(y) >= 2 * m else 0.0
        s0 = (y[:m] / l0) if season == "M" else (y[:m] - l0)
    else:
        l0 = y[0]
        b0 = (y[min(len(y) - 1, 3)] - y[0]) / max(min(len(y) - 1, 3), 1) if trend != "N" else 0.0
        s0 = np.zeros(1)
    return l0, b0, s0


def forecast_from(state, h, phi, trend, season, m, a, b, g, n0):
    l, bt, s, n = state
    out = np.empty(h)
    for k in range(1, h + 1):
        dsum = sum(phi ** i for i in range(1, k + 1)) if trend != "N" else 0.0
        base = l + dsum * bt
        idx = (n + k - 1) % m
        out[k - 1] = base * s[idx] if season == "M" else base + (s[idx] if season == "A" else 0.0)
    return out


def fit_model(y, trend, season, m):
    init = initial(y, trend, season, m)
    damped = trend == "D"

    def unpack(p):
        a = p[0]
        b = p[1] * a if trend != "N" else 0.0
        g = p[2] * (1 - a) if season != "N" else 0.0
        phi = p[3] if damped else 1.0
        return a, b, g, phi

    def sse(p):
        a, b, g, phi = unpack(p)
        f, _ = run_hw(y, a, b, g, phi, trend, season, m, init)
        e = y - f
        v = float(np.dot(e, e))
        return v if np.isfinite(v) else 1e300

    x0 = [0.3, 0.1, 0.1, 0.95]
    bnds = [(0.0001, 0.9999), (0.0, 1.0), (0.0, 1.0), (0.8, 0.98)]
    r = minimize(sse, x0, method="L-BFGS-B", bounds=bnds, options={"maxiter": 300})
    a, b, g, phi = unpack(r.x)
    f, state = run_hw(y, a, b, g, phi, trend, season, m, init)
    e = y - f
    n = len(y)
    k = 1 + (trend != "N") + (season != "N") + damped + 1 + (trend != "N") + (m if season != "N" else 0)
    s2 = float(np.dot(e, e)) / n
    aicc = n * math.log(max(s2, 1e-300)) + 2 * k + (2 * k * (k + 1) / (n - k - 1) if n - k - 1 > 0 else 1e6)
    return {"trend": trend, "season": season, "a": a, "b": b, "g": g, "phi": phi, "fit": f, "state": state, "resid": e, "aicc": aicc, "init": init}


def candidates(y, m):
    trends = {"AUTO": ["N", "A", "D"], "NONE": ["N"], "ADDITIVE": ["A"], "DAMPED": ["D"]}[trend_opt]
    can_season = m > 1 and len(y) >= 2 * m
    seasons = {"AUTO": ["N", "A", "M"], "NONE": ["N"], "ADDITIVE": ["A"], "MULTIPLICATIVE": ["M"]}[season_opt]
    if not can_season:
        seasons = ["N"]
    if (y <= 0).any():
        seasons = [s for s in seasons if s != "M"] or ["N"]
    return [(t, s) for t in trends for s in seasons]


def best_model(y, m):
    fits = [fit_model(y, t, s, m) for t, s in candidates(y, m)]
    return min(fits, key=lambda f: f["aicc"])


def simulate(model, y, h, rng):
    """Future paths with resampled one-step errors pushed through the model's recursion."""
    a, b, g, phi = model["a"], model["b"], model["g"], model["phi"]
    trend, season = model["trend"], model["season"]
    resid = model["resid"][max(1, len(model["resid"]) // 10):]
    resid = resid - resid.mean() if len(resid) else np.zeros(1)
    paths = np.empty((sims, h))
    l0, b0, s0, n = model["state"]
    for i in range(sims):
        l, bt, s = l0, b0, list(s0)
        for k in range(h):
            idx = (n + k) % m
            sv = s[idx] if season != "N" else (1.0 if season == "M" else 0.0)
            damp = phi * bt if trend != "N" else 0.0
            base = l + damp
            yhat = base * sv if season == "M" else base + sv
            yt = yhat + resid[rng.integers(0, len(resid))]
            paths[i, k] = yt
            if season == "M":
                l_new = a * (yt / sv) + (1 - a) * base
                s[idx] = g * (yt / l_new) + (1 - g) * sv if l_new != 0 else sv
            elif season == "A":
                l_new = a * (yt - sv) + (1 - a) * base
                s[idx] = g * (yt - l_new) + (1 - g) * sv
            else:
                l_new = a * yt + (1 - a) * base
            if trend != "N":
                bt = b * (l_new - l) + (1 - b) * damp
            l = l_new
    return paths


w = pd.DataFrame({"t": to_date(df[date_f]), "v": pd.to_numeric(df[value_f], errors="coerce").astype("float64")})
for gname in series_fields:
    w[gname] = df[gname].astype(object).where(df[gname].notna(), "(blank)").map(str)
bad = int(w["t"].isna().sum())
w = w.dropna(subset=["t"])
w["p"] = w["t"].dt.to_period(FREQ[period])
rng = np.random.default_rng(seed)
rows, mrows = [], []
groups = [] if w.empty else [((), w)] if not series_fields else [((k if isinstance(k, tuple) else (k,)), g) for k, g in w.groupby(series_fields, sort=True)]
NAME = {"N": "N", "A": "A", "D": "Ad", "M": "M"}
for key, g in groups:
    gd = dict(zip(series_fields, key))
    s = g.groupby("p")["v"].sum(min_count=1)
    full = pd.period_range(s.index.min(), s.index.max(), freq=FREQ[period])
    s = s.reindex(full).fillna(0.0)
    y = s.to_numpy(dtype=float)
    n = len(y)
    if n < 4:
        mrows.append({**gd, "Model": "Not fitted", "Note": f"Only {n} periods of history (need at least 4)."})
        for p_, v in zip(s.index, y):
            rows.append({**gd, "Period": p_.start_time, "Row Type": "Actual", "Actual": v})
        continue
    mm = m if n >= 2 * m else 1
    rec = {**gd}
    if holdout > 0 and n - holdout >= max(2 * mm, 6):
        tr = y[:-holdout]
        hm = best_model(tr, mm)
        fc = forecast_from(hm["state"], holdout, hm["phi"], hm["trend"], hm["season"], mm, hm["a"], hm["b"], hm["g"], len(tr))
        act = y[-holdout:]
        err = act - fc
        snaive = np.array([tr[len(tr) - mm + (k % mm)] if mm > 1 else tr[-1] for k in range(holdout)])
        mae_naive = float(np.mean(np.abs(act - snaive)))
        rec.update({"Holdout Periods": holdout, "Holdout Model": f"ETS(A,{NAME[hm['trend']]},{NAME[hm['season']]})",
                    "Holdout MAE": float(np.mean(np.abs(err))), "Holdout RMSE": float(np.sqrt(np.mean(err ** 2))),
                    "Holdout MAPE": float(np.mean(np.abs(err[act != 0] / act[act != 0]))) if (act != 0).any() else np.nan,
                    "Seasonal Naive MAE": mae_naive, "MASE": float(np.mean(np.abs(err))) / mae_naive if mae_naive > 0 else np.nan})
        for k, p_ in enumerate(s.index[-holdout:]):
            rows.append({**gd, "Period": p_.start_time, "Row Type": "Holdout forecast", "Forecast": float(fc[k])})
    md = best_model(y, mm)
    fc = forecast_from(md["state"], horizon, md["phi"], md["trend"], md["season"], mm, md["a"], md["b"], md["g"], n)
    paths = simulate(md, y, horizon, rng)
    q = np.percentile(paths, [2.5, 10, 90, 97.5], axis=0)
    rec.update({"Model": f"ETS(A,{NAME[md['trend']]},{NAME[md['season']]})", "Season Length": mm if md["season"] != "N" else None,
                "Alpha": md["a"], "Beta": md["b"] if md["trend"] != "N" else np.nan, "Gamma": md["g"] if md["season"] != "N" else np.nan,
                "Phi": md["phi"] if md["trend"] == "D" else np.nan, "AICc": md["aicc"], "History Periods": n,
                "In-Sample RMSE": float(np.sqrt(np.mean(md["resid"] ** 2))), "Last Actual": float(y[-1]), "Forecast Total": float(fc.sum()),
                "Note": None if mm == m else f"Fewer than two seasons of history ({n} periods): no seasonality."})
    mrows.append(rec)
    for p_, v, f in zip(s.index, y, md["fit"]):
        rows.append({**gd, "Period": p_.start_time, "Row Type": "Actual", "Actual": v, "Fitted": float(f)})
    fut = pd.period_range(s.index[-1] + 1, periods=horizon, freq=FREQ[period])
    for k, p_ in enumerate(fut):
        rows.append({**gd, "Period": p_.start_time, "Row Type": "Forecast", "Forecast": float(fc[k]), "Lower 95": float(q[0, k]), "Lower 80": float(q[1, k]),
                     "Upper 80": float(q[2, k]), "Upper 95": float(q[3, k]), "Horizon": k + 1})

fcols = series_fields + ["Period", "Row Type", "Actual", "Fitted", "Forecast", "Lower 95", "Lower 80", "Upper 80", "Upper 95", "Horizon"]
out = pd.DataFrame(rows, columns=fcols)
out["Period"] = pd.to_datetime(out["Period"]).dt.tz_localize("UTC") if len(out) else pd.Series([], dtype="datetime64[ns, UTC]")
ORDER = {"Actual": 0, "Holdout forecast": 1, "Forecast": 2}
out = out.sort_values(series_fields + ["Period", "Row Type"], key=lambda c: c.map(ORDER) if c.name == "Row Type" else c, kind="mergesort").reset_index(drop=True)
for c in ("Actual", "Fitted", "Forecast", "Lower 95", "Lower 80", "Upper 80", "Upper 95"):
    out[c] = out[c].astype("float64")
out["Horizon"] = pd.array(out["Horizon"].to_numpy(dtype=float), dtype="Float64").astype("Int64")
mcols = series_fields + ["Model", "Season Length", "Alpha", "Beta", "Gamma", "Phi", "AICc", "History Periods", "In-Sample RMSE", "Last Actual", "Forecast Total",
                         "Holdout Periods", "Holdout Model", "Holdout MAE", "Holdout RMSE", "Holdout MAPE", "Seasonal Naive MAE", "MASE", "Note"]
models = pd.DataFrame(mrows, columns=mcols)
for c in ("Season Length", "History Periods", "Holdout Periods"):
    models[c] = pd.array(pd.to_numeric(models[c], errors="coerce").to_numpy(dtype=float), dtype="Float64").astype("Int64")
for c in ("Alpha", "Beta", "Gamma", "Phi", "AICc", "In-Sample RMSE", "Last Actual", "Forecast Total", "Holdout MAE", "Holdout RMSE", "Holdout MAPE",
          "Seasonal Naive MAE", "MASE"):
    models[c] = models[c].astype("float64")

omniscope_api.write_output(out, "forecast")
omniscope_api.write_output(models, "models")
fitted = models[models["Model"] != "Not fitted"]
msg = f"{len(groups):,} series forecast {horizon} {period.lower()}s ahead"
if len(fitted):
    msg += "; models: " + ", ".join(f"{k} x{v}" for k, v in fitted["Model"].value_counts().items())
if holdout and fitted["MASE"].notna().any():
    msg += f"; holdout MASE median {fitted['MASE'].median():.2f}"
omniscope_api.close(msg + (f"; {bad:,} rows without a valid date skipped" if bad else "") + ".")
