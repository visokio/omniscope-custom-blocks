"""Stock Run-Out Projection: project each item's stock forward day by day from
stock on hand, expected demand (forecast or orders) and expected receipts
(open purchase orders, transfers), and report when it runs out.

Input 1: one row per item with stock on hand and, optionally, a safety stock
and a steady daily demand. Input 2 (optional): dated future movements per item
(quantity and a type: receipts such as PO / receipt / transfer in; anything
else counts as demand).

Per item: projected run-out date, days of cover, first day below safety stock,
lowest projected stock (shortfall), next receipt, and a status such as
"Runs out before next receipt", so buyers know what to expedite.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


i_item, i_stock, i_ss, i_daily = opt("item_field"), opt("stock_field"), opt("safety_field"), opt("daily_demand_field")
m_item, m_date, m_qty, m_type = opt("move_item_field"), opt("move_date_field"), opt("move_qty_field"), opt("move_type_field")
start_txt = opt("start_date", "")
horizon = int(opt("horizon_days", 90))
receipt_words = opt("receipt_words", "receipt, po, purchase, transfer in, supply, inbound")

I = omniscope_api.read_input_records(input_number=0)
M = omniscope_api.read_input_records(input_number=1)
if I is None:
    omniscope_api.abort("Connect the items with stock on hand to input 1.")
for f, lab in ((i_item, "item"), (i_stock, "stock on hand")):
    if not f or f not in I.columns:
        omniscope_api.abort(f"Choose the {lab} field of input 1 (got '{f}').")
for f in (i_ss, i_daily):
    if f and f not in I.columns:
        omniscope_api.abort(f"Field '{f}' is not in input 1.")
if M is not None:
    for f, lab in ((m_item, "item"), (m_date, "date"), (m_qty, "quantity")):
        if not f or f not in M.columns:
            omniscope_api.abort(f"Choose the {lab} field of input 2 (got '{f}').")
    if m_type and m_type not in M.columns:
        omniscope_api.abort(f"Field '{m_type}' is not in input 2.")
elif not i_daily:
    omniscope_api.abort("Give a daily demand field on input 1, or connect future movements to input 2.")
if not 1 <= horizon <= 3660:
    omniscope_api.abort("Horizon must be 1 to 3,660 days.")


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


key = lambda s: s.astype(object).where(s.notna(), "(blank)").map(lambda v: str(int(v)) if isinstance(v, float) and v.is_integer() else str(v))
items = pd.DataFrame({"item": key(I[i_item]), "stock": pd.to_numeric(I[i_stock], errors="coerce").fillna(0).astype("float64"),
                      "ss": pd.to_numeric(I[i_ss], errors="coerce").fillna(0).astype("float64") if i_ss else 0.0,
                      "daily": pd.to_numeric(I[i_daily], errors="coerce").fillna(0).astype("float64") if i_daily else 0.0})
items = items.groupby("item", sort=False).agg(stock=("stock", "sum"), ss=("ss", "max"), daily=("daily", "max")).reset_index()
words = [re.escape(w.strip()) for w in receipt_words.split(",") if w.strip()]
rx = re.compile(r"\b(" + "|".join(words) + r")\b" if words else "$^", re.I)
mv = pd.DataFrame(columns=["item", "d", "dem", "rec"])
if M is not None:
    q = pd.to_numeric(M[m_qty], errors="coerce").astype("float64")
    t = M[m_type].astype(object).where(M[m_type].notna(), "").map(str) if m_type else pd.Series([""] * len(M))
    is_rec = t.map(lambda v: bool(rx.search(v))).to_numpy()
    mv = pd.DataFrame({"item": key(M[m_item]), "d": to_date(M[m_date]), "dem": np.where(is_rec, 0.0, q.abs()), "rec": np.where(is_rec, q.abs(), 0.0)}).dropna(subset=["d"])
if start_txt:
    start = to_date(pd.Series([start_txt], dtype=object)).iloc[0]
    if pd.isna(start):
        omniscope_api.abort("The start date must be a date, such as 2025-11-03.")
else:
    start = mv["d"].min() if len(mv) else pd.Timestamp.today().normalize()
days = pd.date_range(start, periods=horizon, freq="D")
before = int((mv["d"] < start).sum()) if len(mv) else 0
mv = mv[(mv["d"] >= start) & (mv["d"] <= days[-1])]
unknown = sorted(set(mv["item"]) - set(items["item"]))
dem_t = mv.pivot_table(index="item", columns="d", values="dem", aggfunc="sum", fill_value=0.0).reindex(columns=days, fill_value=0.0) if len(mv) else None
rec_t = mv.pivot_table(index="item", columns="d", values="rec", aggfunc="sum", fill_value=0.0).reindex(columns=days, fill_value=0.0) if len(mv) else None

irows, prow = [], []
for _, it in items.iterrows():
    k = it["item"]
    dem = np.full(horizon, it["daily"]) + (dem_t.loc[k].to_numpy() if dem_t is not None and k in dem_t.index else 0.0)
    rec = rec_t.loc[k].to_numpy() if rec_t is not None and k in rec_t.index else np.zeros(horizon)
    closing = it["stock"] + np.cumsum(rec - dem)
    opening = np.concatenate([[it["stock"]], closing[:-1]])
    out_idx = np.nonzero(closing < 0)[0]
    below_idx = np.nonzero(closing < it["ss"])[0]
    rec_idx = np.nonzero(rec > 0)[0]
    run_out = days[out_idx[0]] if len(out_idx) else pd.NaT
    next_rec = days[rec_idx[0]] if len(rec_idx) else pd.NaT
    if len(out_idx):
        status = "Runs out before next receipt" if (pd.isna(next_rec) or run_out < next_rec) else "Runs out (receipts too small or late)"
    elif len(below_idx):
        status = "Below safety stock"
    else:
        status = "OK"
    avg = dem.mean()
    irows.append({str(i_item): k, "Stock On Hand": it["stock"], "Safety Stock": it["ss"], "Demand In Horizon": float(dem.sum()), "Receipts In Horizon": float(rec.sum()),
                  "Average Daily Demand": float(avg), "Days Of Cover (no receipts)": float(it["stock"] / avg) if avg > 0 else np.nan,
                  "Run-Out Date": run_out, "Days Until Run-Out": int(out_idx[0]) if len(out_idx) else None,
                  "First Day Below Safety Stock": days[below_idx[0]] if len(below_idx) else pd.NaT, "Next Receipt": next_rec,
                  "Lowest Projected Stock": float(closing.min()), "Shortfall": float(max(0.0, -closing.min())),
                  "Stock At Horizon End": float(closing[-1]), "Status": status})
    for di in range(horizon):
        prow.append((k, days[di], opening[di], dem[di], rec[di], closing[di]))
ires = pd.DataFrame(irows)
ORDER = {"Runs out before next receipt": 0, "Runs out (receipts too small or late)": 1, "Below safety stock": 2, "OK": 3}
if len(ires):
    ires["__o"] = ires["Status"].map(ORDER)
    ires = ires.sort_values(["__o", "Run-Out Date", str(i_item)], na_position="last", kind="mergesort").drop(columns="__o").reset_index(drop=True)
    for c in ("Run-Out Date", "First Day Below Safety Stock", "Next Receipt"):
        ires[c] = pd.to_datetime(ires[c]).dt.tz_localize("UTC")
    ires["Days Until Run-Out"] = pd.array(pd.to_numeric(ires["Days Until Run-Out"]).to_numpy(dtype=float), dtype="Float64").astype("Int64")
    for c in ("Stock On Hand", "Safety Stock", "Demand In Horizon", "Receipts In Horizon", "Average Daily Demand", "Days Of Cover (no receipts)",
              "Lowest Projected Stock", "Shortfall", "Stock At Horizon End"):
        ires[c] = ires[c].astype("float64")
proj = pd.DataFrame(prow, columns=[str(i_item), "Date", "Opening Stock", "Demand", "Receipts", "Closing Stock"])
proj["Date"] = pd.to_datetime(proj["Date"]).dt.tz_localize("UTC")
for c in ("Opening Stock", "Demand", "Receipts", "Closing Stock"):
    proj[c] = proj[c].astype("float64")
omniscope_api.write_output(ires, "items")
omniscope_api.write_output(proj, "projection")
n_out = int(ires["Status"].str.startswith("Runs out").sum()) if len(ires) else 0
omniscope_api.close(f"{len(ires):,} items projected {horizon} days from {start.date()}: {n_out:,} run out"
                    + (f", {int((ires['Status'] == 'Below safety stock').sum()):,} dip below safety stock" if len(ires) else "")
                    + (f"; movements for {len(unknown):,} unknown items ignored" if unknown else "") + (f"; {before:,} movements before the start ignored" if before else "") + ".")
