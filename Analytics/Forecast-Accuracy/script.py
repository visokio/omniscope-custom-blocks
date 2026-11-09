"""Forecast Accuracy: compare one or more forecast fields with the actuals and
report the standard accuracy measures per item (and per forecast / model),
overall per model, and per row:

  MAE, RMSE, MAPE (rows with actual 0 excluded), sMAPE, WAPE (= sum|error| /
  sum actual), accuracy (1 - WAPE), bias (sum(forecast - actual) / sum actual),
  and the tracking signal (cumulative error / mean absolute error, in period
  order), with flags for biased or out-of-control forecasts and the best model
  per item.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


actual_f = opt("actual_field")
forecast_fs = opt("forecast_fields", []) or []
item_fields = opt("item_fields", []) or []
period_f = opt("period_field")
best_by = opt("best_by", "WAPE")
bias_limit = float(opt("bias_limit", 0.1))
ts_limit = float(opt("tracking_limit", 4.0))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect actuals and forecasts to the input.")
if not actual_f or actual_f not in df.columns:
    omniscope_api.abort(f"Choose the actual field (got '{actual_f}').")
if not forecast_fs:
    omniscope_api.abort("Choose at least one forecast field.")
miss = [f for f in list(forecast_fs) + list(item_fields) + ([period_f] if period_f else []) if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")
if actual_f in forecast_fs:
    omniscope_api.abort("The actual field cannot also be a forecast field.")

base = df[list(item_fields) + ([period_f] if period_f else [])].copy()
for c in item_fields:
    base[c] = base[c].astype(object).where(base[c].notna(), "(blank)")
base["__a"] = pd.to_numeric(df[actual_f], errors="coerce").astype("float64")
base["__row"] = np.arange(len(df))
long = []
for f in forecast_fs:
    t = base.copy()
    t["Model"] = str(f)
    t["__f"] = pd.to_numeric(df[f], errors="coerce").astype("float64")
    long.append(t)
L = pd.concat(long, ignore_index=True)
L = L[L["__a"].notna() & L["__f"].notna()]
L["Error"] = L["__f"] - L["__a"]
L["Absolute Error"] = L["Error"].abs()
L["Percentage Error"] = np.where(L["__a"] != 0, L["Error"] / L["__a"].abs(), np.nan)
order_cols = list(item_fields) + ["Model"] + ([period_f] if period_f else ["__row"])
L = L.sort_values(order_cols, kind="mergesort")


def metrics(g):
    a, f, e = g["__a"].to_numpy(), g["__f"].to_numpy(), g["Error"].to_numpy()
    n = len(g)
    if n == 0:
        return {}
    sa = np.abs(a).sum()
    mae = np.abs(e).mean()
    nz = a != 0
    mape = np.mean(np.abs(e[nz] / a[nz])) if nz.any() else np.nan
    denom = (np.abs(a) + np.abs(f))
    smape = np.mean(np.where(denom > 0, 2 * np.abs(e) / np.where(denom > 0, denom, 1), 0.0))
    wape = np.abs(e).sum() / sa if sa else np.nan
    bias = e.sum() / sa if sa else np.nan
    ts = e.sum() / mae if mae else 0.0
    return {"Periods": n, "Actual Total": a.sum(), "Forecast Total": f.sum(), "MAE": mae, "RMSE": float(np.sqrt(np.mean(e ** 2))),
            "MAPE": mape, "sMAPE": smape, "WAPE": wape, "Accuracy": (1 - wape) if wape == wape else np.nan, "Bias": bias,
            "Tracking Signal": ts}


rows = []
gb = L.groupby(list(item_fields) + ["Model"], sort=False) if item_fields else L.groupby(["Model"], sort=False)
for k, g in gb:
    k = k if isinstance(k, tuple) else (k,)
    rec = dict(zip(list(item_fields) + ["Model"], k))
    rec.update(metrics(g))
    flags = []
    if rec.get("Bias") == rec.get("Bias") and abs(rec["Bias"]) > bias_limit:
        flags.append("Over-forecasting" if rec["Bias"] > 0 else "Under-forecasting")
    if abs(rec.get("Tracking Signal", 0)) > ts_limit:
        flags.append("Tracking signal out of control")
    rec["Flags"] = "; ".join(flags)
    rows.append(rec)
mcols = list(item_fields) + ["Model", "Periods", "Actual Total", "Forecast Total", "MAE", "RMSE", "MAPE", "sMAPE", "WAPE", "Accuracy", "Bias", "Tracking Signal", "Flags"]
item_df = pd.DataFrame(rows, columns=mcols)
item_df["Periods"] = item_df["Periods"].astype("int64")
for c in mcols[len(item_fields) + 2:-1]:
    item_df[c] = item_df[c].astype("float64")
if item_fields and len(item_df):
    metric_col = {"WAPE": "WAPE", "MAE": "MAE", "RMSE": "RMSE", "MAPE": "MAPE", "ACCURACY": "Accuracy"}[best_by]
    rk = item_df.groupby(list(item_fields))[metric_col].rank(ascending=metric_col != "Accuracy", method="min")
    item_df["Rank For Item"] = pd.array(rk.to_numpy(), dtype="Float64").astype("Int64")
    item_df["Best Model For Item"] = np.where(item_df["Rank For Item"] == 1, "Yes", "No")

overall = []
for mdl, g in L.groupby("Model", sort=False):
    rec = {"Model": mdl, **metrics(g)}
    rec.pop("Tracking Signal", None)  # per item only: summed across items it has no meaning
    if item_fields and len(item_df):
        rec["Items Where Best"] = int(((item_df["Model"] == mdl) & (item_df["Best Model For Item"] == "Yes")).sum())
        rec["Items"] = int(item_df[item_df["Model"] == mdl].shape[0])
    overall.append(rec)
ov = pd.DataFrame(overall)
if len(ov):
    ov["Rank"] = pd.array(ov["WAPE" if best_by != "ACCURACY" else "Accuracy"].rank(ascending=best_by != "ACCURACY", method="min").to_numpy(), dtype="Float64").astype("Int64")
    for c in ov.columns:
        if c in ("Periods", "Items Where Best", "Items"):
            ov[c] = ov[c].astype("int64")
        elif c not in ("Model", "Rank"):
            ov[c] = ov[c].astype("float64")

err = L.rename(columns={"__a": "Actual", "__f": "Forecast"}).drop(columns=["__row"])
err = err[list(item_fields) + ([period_f] if period_f else []) + ["Model", "Actual", "Forecast", "Error", "Absolute Error", "Percentage Error"]]
for c in ("Actual", "Forecast", "Error", "Absolute Error", "Percentage Error"):
    err[c] = err[c].astype("float64")

omniscope_api.write_output(item_df, "items")
omniscope_api.write_output(ov, "models")
omniscope_api.write_output(err.reset_index(drop=True), "errors")
best = ov.sort_values("Rank").iloc[0]["Model"] if len(ov) else "-"
omniscope_api.close(f"{len(forecast_fs)} forecast(s) compared over {len(err):,} rows; best overall by {best_by}: {best}.")
