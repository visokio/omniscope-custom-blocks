"""Price-Volume-Mix Bridge: explain the change in revenue between a base period
and a current period as

  Volume    more or fewer units overall, at base mix and base prices
  Mix       a shift between products of different base price
  Price     price changes on the units sold now
  New       revenue from products not sold in the base period
  Lost      revenue lost from products no longer sold

computed over the items you choose (product, SKU, service), optionally per
group (region, channel). The effects add up exactly to the revenue change.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


period_f = opt("period_field")
item_f = opt("item_field")
volume_f = opt("volume_field")
revenue_f = opt("revenue_field")
group_fields = opt("group_fields", []) or []
base_label = opt("base_period", "")
cur_label = opt("current_period", "")

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the sales data to the input.")
for f, label in ((period_f, "period"), (item_f, "item"), (volume_f, "volume"), (revenue_f, "revenue")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
miss = [g for g in group_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Group fields not in the input: {', '.join(miss)}")


def lab(v):
    if v is None or (isinstance(v, float) and v != v):
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    return str(v)


w = pd.DataFrame({"per": df[period_f].map(lab), "item": df[item_f].map(lab),
                  "q": pd.to_numeric(df[volume_f], errors="coerce").astype("float64").fillna(0.0),
                  "r": pd.to_numeric(df[revenue_f], errors="coerce").astype("float64").fillna(0.0)})  # float, not Int64 (avoids pd.NA)
for g in group_fields:
    w[g] = df[g].map(lab).fillna("(blank)")
w = w.dropna(subset=["per", "item"])
periods = sorted(w["per"].unique())
if not base_label or not cur_label:
    if len(periods) < 2:
        omniscope_api.abort("The period field needs at least two values (base and current).")
    base_label = base_label or periods[0]
    cur_label = cur_label or periods[-1]
for p_, nm in ((base_label, "Base"), (cur_label, "Current")):
    if p_ not in periods:
        omniscope_api.abort(f"{nm} period '{p_}' not found in the period field; values are: {', '.join(periods[:10])}")

STEPS = ["Base revenue", "Volume", "Mix", "Price", "New products", "Lost products", "Current revenue"]
bridge_rows, detail_rows = [], []
groups = [((), w)] if not group_fields else [((k if isinstance(k, tuple) else (k,)), g) for k, g in w.groupby(group_fields, sort=True)]
for key, g in groups:
    gd = {c: key[i] for i, c in enumerate(group_fields)}
    a = g.groupby(["item", "per"])[["q", "r"]].sum().unstack("per").fillna(0.0)
    q0 = a[("q", base_label)] if ("q", base_label) in a.columns else pd.Series(0.0, index=a.index)
    q1 = a[("q", cur_label)] if ("q", cur_label) in a.columns else pd.Series(0.0, index=a.index)
    r0 = a[("r", base_label)] if ("r", base_label) in a.columns else pd.Series(0.0, index=a.index)
    r1 = a[("r", cur_label)] if ("r", cur_label) in a.columns else pd.Series(0.0, index=a.index)
    cont = (q0 > 0) & (q1 > 0)
    new = (q0 <= 0) & (q1 > 0)
    lost = (q0 > 0) & (q1 <= 0)
    other = ~(cont | new | lost)  # revenue without volume (fees, adjustments)
    p0 = (r0 / q0).where(q0 > 0)
    p1 = (r1 / q1).where(q1 > 0)
    Q0, Q1 = q0[cont].sum(), q1[cont].sum()
    s0 = (q0 / Q0).where(cont, 0.0) if Q0 else q0 * 0
    s1 = (q1 / Q1).where(cont, 0.0) if Q1 else q1 * 0
    vol = ((Q1 - Q0) * s0 * p0).where(cont, 0.0)
    mix = (Q1 * (s1 - s0) * p0).where(cont, 0.0)
    price = (q1 * (p1 - p0)).where(cont, 0.0)
    newv = r1.where(new, 0.0) + (r1 - r0).where(other, 0.0)
    lostv = (-r0).where(lost, 0.0)
    R0, R1 = float(r0.sum()), float(r1.sum())
    vals = [R0, float(vol.sum()), float(mix.sum()), float(price.sum()), float(newv.sum()), float(lostv.sum()), R1]
    run_ = R0
    for i, (st, v) in enumerate(zip(STEPS, vals)):
        if i in (0, len(STEPS) - 1):
            start, end = 0.0, v
        else:
            start, end = run_, run_ + v
            run_ = end
        bridge_rows.append({**gd, "Step Number": i + 1, "Step": st, "Value": v, "Bar Start": start, "Bar End": end,
                            "Share Of Change": (v / (R1 - R0)) if 0 < i < len(STEPS) - 1 and R1 != R0 else np.nan})
    for it in a.index:
        status = "Continuing" if cont[it] else "New" if new[it] else "Lost" if lost[it] else "No volume"
        detail_rows.append({**gd, "Item": it, "Status": status, f"Volume {base_label}": q0[it], f"Volume {cur_label}": q1[it],
                            f"Revenue {base_label}": r0[it], f"Revenue {cur_label}": r1[it],
                            f"Price {base_label}": p0[it], f"Price {cur_label}": p1[it],
                            "Volume Effect": vol[it], "Mix Effect": mix[it], "Price Effect": price[it],
                            "New / Lost Effect": newv[it] + lostv[it], "Revenue Change": r1[it] - r0[it]})

bdf = pd.DataFrame(bridge_rows)
bdf["Step Number"] = bdf["Step Number"].astype("int64")
for c in ("Value", "Bar Start", "Bar End", "Share Of Change"):
    bdf[c] = bdf[c].astype("float64")
ddf = pd.DataFrame(detail_rows)
for c in ddf.columns:
    if c not in list(group_fields) + ["Item", "Status"]:
        ddf[c] = ddf[c].astype("float64")
omniscope_api.write_output(bdf, "bridge")
omniscope_api.write_output(ddf, "items")
tot = bdf[bdf["Step"] == "Current revenue"]["Value"].sum() - bdf[bdf["Step"] == "Base revenue"]["Value"].sum()
omniscope_api.close(f"{base_label} to {cur_label}: revenue change {tot:,.2f} explained across {len(groups):,} group(s).")
