"""Cost Allocation: apportion cost pools (IT, facilities, HR, finance) to
receivers (departments, products, customers, sites) in proportion to a driver
(headcount, floor area, tickets, revenue), with penny-exact rounding so the
allocations add up to each pool exactly (largest-remainder method).

Input 1: cost pools, one row per pool with its amount and the name of its
driver. Input 2: driver values, one row per receiver and driver (long form:
receiver, driver, value), or one column per driver (wide form).
Outputs: every allocation, a summary per receiver (total and per pool), and
any pool that could not be allocated (no driver values).
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


pool_f, amt_f, pdrv_f = opt("pool_field"), opt("amount_field"), opt("pool_driver_field")
rec_f, drv_f, val_f = opt("receiver_field"), opt("driver_field"), opt("value_field")
default_driver = opt("default_driver", "")
decimals = int(opt("decimals", 2))

P = omniscope_api.read_input_records(input_number=0)
D = omniscope_api.read_input_records(input_number=1)
if P is None or D is None:
    omniscope_api.abort("Connect the cost pools to input 1 and the driver values to input 2.")
for df, f, lab in ((P, pool_f, "pool"), (P, amt_f, "amount"), (D, rec_f, "receiver")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
if pdrv_f and pdrv_f not in P.columns:
    omniscope_api.abort(f"Field '{pdrv_f}' is not in input 1.")
long_form = bool(drv_f and val_f)
if long_form:
    for f in (drv_f, val_f):
        if f not in D.columns:
            omniscope_api.abort(f"Field '{f}' is not in input 2.")
    dl = pd.DataFrame({"r": D[rec_f].astype(object).map(str), "d": D[drv_f].astype(object).map(lambda v: str(v).strip()),
                       "v": pd.to_numeric(D[val_f], errors="coerce").astype("float64")})
else:
    cols = [c for c in D.columns if c != rec_f and pd.api.types.is_numeric_dtype(D[c])]
    if not cols:
        omniscope_api.abort("Input 2 needs either driver and value fields (long form) or numeric driver columns (wide form).")
    dl = D[[rec_f] + cols].melt(id_vars=[rec_f], var_name="d", value_name="v").rename(columns={rec_f: "r"})
    dl["r"] = dl["r"].astype(object).map(str)
    dl["v"] = pd.to_numeric(dl["v"], errors="coerce").astype("float64")
dl = dl.dropna(subset=["v"])
neg = dl[dl["v"] < 0]
if len(neg):
    omniscope_api.abort(f"Driver values must not be negative (receiver {neg['r'].iloc[0]}, driver {neg['d'].iloc[0]}).")
dl = dl.groupby(["d", "r"], sort=False)["v"].sum().reset_index()
scale = 10 ** decimals


def largest_remainder(amount, weights):
    """Split amount by weights into multiples of 1/scale that add up exactly."""
    w = np.asarray(weights, dtype=float)
    units = int(round(amount * scale))
    raw = units * w / w.sum()
    base = np.floor(raw).astype(np.int64) if units >= 0 else np.ceil(raw).astype(np.int64)
    left = units - int(base.sum())
    frac = raw - base
    order = np.argsort(-frac if left >= 0 else frac, kind="stable")
    base[order[:abs(left)]] += 1 if left >= 0 else -1
    return base / scale


arows, unalloc = [], []
for _, p in P.iterrows():
    pool = str(p[pool_f])
    amount = pd.to_numeric(pd.Series([p[amt_f]]), errors="coerce").iloc[0]
    driver = str(p[pdrv_f]).strip() if pdrv_f and pd.notna(p[pdrv_f]) else default_driver
    if amount != amount:
        unalloc.append({"Pool": pool, "Amount": np.nan, "Driver": driver, "Reason": "Amount is not a number"})
        continue
    g = dl[dl["d"].str.lower() == str(driver).lower()]
    g = g[g["v"] > 0]
    if not driver or g.empty:
        unalloc.append({"Pool": pool, "Amount": float(amount), "Driver": driver or None, "Reason": "No driver values for this driver" if driver else "No driver given"})
        continue
    alloc = largest_remainder(float(amount), g["v"].to_numpy())
    tot = g["v"].sum()
    for (r, v), a in zip(zip(g["r"], g["v"]), alloc):
        arows.append({"Pool": pool, "Receiver": r, "Driver": driver, "Driver Value": float(v), "Share": float(v / tot), "Allocated": float(a)})
al = pd.DataFrame(arows, columns=["Pool", "Receiver", "Driver", "Driver Value", "Share", "Allocated"])
for c in ("Driver Value", "Share", "Allocated"):
    al[c] = al[c].astype("float64")
if len(al):
    wide = al.pivot_table(index="Receiver", columns="Pool", values="Allocated", aggfunc="sum", fill_value=0.0)
    wide.columns = [f"From {c}" for c in wide.columns]
    wide.insert(0, "Total Allocated", wide.sum(axis=1).round(decimals))
    wide = wide.sort_values("Total Allocated", ascending=False).reset_index()
    wide["Share Of All Costs"] = wide["Total Allocated"] / wide["Total Allocated"].sum()
else:
    wide = pd.DataFrame({"Receiver": pd.Series([], dtype=object), "Total Allocated": pd.Series([], dtype="float64")})
for c in wide.columns[1:]:
    wide[c] = wide[c].astype("float64")
un = pd.DataFrame(unalloc, columns=["Pool", "Amount", "Driver", "Reason"])
un["Amount"] = un["Amount"].astype("float64")
al = al.rename(columns={"Receiver": str(rec_f)})
wide = wide.rename(columns={"Receiver": str(rec_f)})
omniscope_api.write_output(al, "allocations")
omniscope_api.write_output(wide, "receivers")
omniscope_api.write_output(un, "unallocated")
omniscope_api.close(f"{P.shape[0] - len(un):,} of {P.shape[0]:,} pools allocated to {wide.shape[0]:,} receivers; total {al['Allocated'].sum():,.{decimals}f}"
                    + (f"; {len(un)} pool(s) not allocated" if len(un) else "") + ".")
