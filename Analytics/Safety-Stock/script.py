"""Safety Stock and Reorder Point: from demand history per item (and optional
item parameters), calculate for a target service level

  average demand and standard deviation per period (periods with no demand
  count as zero), safety stock  z * sqrt(L * sd_d^2 + d^2 * sd_L^2),
  reorder point  d * L + safety stock,  order-up-to level for periodic review,
  economic order quantity (when unit cost, ordering cost and holding rate are
  known), cover in periods, and a reorder list from current stock.

Input 1: demand lines (item, date, quantity). Input 2 (optional): one row per
item with lead time (in periods), lead-time standard deviation, unit cost,
stock on hand and service level overrides.
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


item_f = opt("item_field")
date_f = opt("date_field")
qty_f = opt("quantity_field")
period = opt("period", "WEEK")
service = float(opt("service_level", 0.95))
lead_default = float(opt("lead_time", 2.0))
review = float(opt("review_period", 1.0))
order_cost = float(opt("ordering_cost", 0.0) or 0.0)
holding_rate = float(opt("holding_rate", 0.25))
p_item = opt("param_item_field")
p_lead = opt("param_lead_field")
p_lead_sd = opt("param_lead_sd_field")
p_cost = opt("param_cost_field")
p_stock = opt("param_stock_field")
p_service = opt("param_service_field")
FREQ = {"DAY": "D", "WEEK": "W-SUN", "MONTH": "M"}
PER_YEAR = {"DAY": 365.0, "WEEK": 52.0, "MONTH": 12.0}

dem = omniscope_api.read_input_records(input_number=0)
par = omniscope_api.read_input_records(input_number=1)
if dem is None:
    omniscope_api.abort("Connect demand history to input 1.")
for f, label in ((item_f, "item"), (date_f, "date"), (qty_f, "quantity")):
    if not f or f not in dem.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
if not 0.5 <= service < 1:
    omniscope_api.abort("Service level must be between 0.5 and 0.9999, for example 0.95.")
if par is not None:
    if not p_item or p_item not in par.columns:
        omniscope_api.abort("Choose the item field of the parameters input (input 2).")
    for f in (p_lead, p_lead_sd, p_cost, p_stock, p_service):
        if f and f not in par.columns:
            omniscope_api.abort(f"Field '{f}' is not in the parameters input.")


def norm_ppf(p):
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p > 1 - 0.02425:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


d = dem[date_f]
if pd.api.types.is_datetime64_any_dtype(d):
    dates = d.dt.tz_localize(None) if d.dt.tz is not None else d
else:
    txt = d.astype(object).where(d.notna(), None).astype(str).str.strip()
    iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
    dates = pd.Series(pd.NaT, index=d.index, dtype="datetime64[ns]")
    dates[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
    dates[~iso & d.notna()] = pd.to_datetime(txt[~iso & d.notna()], errors="coerce", dayfirst=True, format="mixed")
w = pd.DataFrame({"item": dem[item_f].astype(object), "p": dates.dt.to_period(FREQ[period]),
                  "q": pd.to_numeric(dem[qty_f], errors="coerce").astype("float64")}).dropna(subset=["item", "p"])
w["q"] = w["q"].fillna(0.0)
last_p = w["p"].max() if len(w) else None

params = {}
if par is not None:
    for _, r in par.iterrows():
        params[r[p_item]] = r

rows = []
for it, g in w.groupby("item", sort=True):
    s = g.groupby("p")["q"].sum()
    full = pd.period_range(s.index.min(), last_p, freq=FREQ[period])  # zero demand counts, up to the latest period overall
    s = s.reindex(full, fill_value=0.0)
    n = len(s)
    mean = float(s.mean())
    sd = float(s.std(ddof=1)) if n > 1 else 0.0
    pr = params.get(it)

    def pget(field, default):
        if pr is None or not field:
            return default
        v = pd.to_numeric(pd.Series([pr[field]]), errors="coerce").iloc[0]
        return default if pd.isna(v) else float(v)
    L = pget(p_lead, lead_default)
    sdL = pget(p_lead_sd, 0.0)
    sl = pget(p_service, service)
    sl = min(max(sl, 0.5), 0.9999)
    z = norm_ppf(sl)
    ss = z * math.sqrt(max(L, 0) * sd ** 2 + mean ** 2 * sdL ** 2)
    rop = mean * L + ss
    out_to = mean * (L + review) + z * math.sqrt(max(L + review, 0) * sd ** 2 + mean ** 2 * sdL ** 2)
    cost = pget(p_cost, np.nan)
    stock = pget(p_stock, np.nan)
    annual = mean * PER_YEAR[period]
    eoq = math.sqrt(2 * annual * order_cost / (holding_rate * cost)) if order_cost > 0 and cost == cost and cost > 0 and holding_rate > 0 else np.nan
    cover = stock / mean if stock == stock and mean > 0 else np.nan
    status = ("Below reorder point" if stock == stock and stock <= rop else "OK" if stock == stock else "No stock figure")
    order_qty = max(0.0, out_to - stock) if status == "Below reorder point" else 0.0
    rows.append({"Item": it, "Periods Of History": n, "Average Demand": mean, "Demand Std Dev": sd,
                 "Coefficient Of Variation": sd / mean if mean else np.nan, "Lead Time": L, "Lead Time Std Dev": sdL,
                 "Service Level": sl, "Z": z, "Safety Stock": ss, "Reorder Point": rop, "Order-Up-To Level": out_to,
                 "EOQ": eoq, "Safety Stock Value": ss * cost if cost == cost else np.nan, "Stock On Hand": stock,
                 "Cover (periods)": cover, "Status": status, "Suggested Order": order_qty})
res = pd.DataFrame(rows, columns=["Item", "Periods Of History", "Average Demand", "Demand Std Dev", "Coefficient Of Variation", "Lead Time",
                                  "Lead Time Std Dev", "Service Level", "Z", "Safety Stock", "Reorder Point", "Order-Up-To Level", "EOQ",
                                  "Safety Stock Value", "Stock On Hand", "Cover (periods)", "Status", "Suggested Order"])
res["Periods Of History"] = res["Periods Of History"].astype("int64")
for c in res.columns:
    if c not in ("Item", "Periods Of History", "Status"):
        res[c] = res[c].astype("float64")
res = res.rename(columns={"Item": str(item_f)})
reorder = res[res["Status"] == "Below reorder point"].sort_values("Cover (periods)").reset_index(drop=True)

omniscope_api.write_output(res, "levels")
omniscope_api.write_output(reorder, "reorder")
omniscope_api.close(f"{len(res):,} items; {len(reorder):,} at or below their reorder point (service level {service:.0%}, {period.lower()}ly periods).")
