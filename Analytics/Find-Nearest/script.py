"""Find Nearest: for each point in the first input (customers, incidents,
properties) find the k nearest points in the second input (stores, depots,
engineers, competitors) by great-circle distance, optionally within a maximum
distance, with the compass direction; plus a catchment summary per
destination.

Pure numpy (haversine,
processed in chunks).
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


o_lat, o_lon = opt("origin_lat"), opt("origin_lon")
d_lat, d_lon = opt("dest_lat"), opt("dest_lon")
d_id = opt("dest_id")
k = int(opt("k", 1))
max_dist = float(opt("max_distance", 0) or 0)
unit = opt("unit", "KM")
keep_unmatched = opt("keep_unmatched", True)

origins = omniscope_api.read_input_records(input_number=0)
dests = omniscope_api.read_input_records(input_number=1)
if origins is None or dests is None:
    omniscope_api.abort("Connect the points to search from to input 1 and the points to find to input 2.")
for f, df, label in ((o_lat, origins, "first"), (o_lon, origins, "first"), (d_lat, dests, "second"), (d_lon, dests, "second")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose latitude and longitude fields that exist in the {label} input (got '{f}').")
if d_id and d_id not in dests.columns:
    omniscope_api.abort(f"Destination name field '{d_id}' is not in the second input.")
if k < 1:
    omniscope_api.abort("Number of nearest points must be at least 1.")

R = 6371.0088 if unit == "KM" else 3958.7613
dist_col = "Distance (km)" if unit == "KM" else "Distance (miles)"


def coords(df, la, lo):
    lat = pd.to_numeric(df[la], errors="coerce").astype("float64").to_numpy()
    lon = pd.to_numeric(df[lo], errors="coerce").astype("float64").to_numpy()
    ok = np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) <= 90) & (np.abs(lon) <= 180)
    return np.radians(lat), np.radians(lon), ok


olat, olon, ook = coords(origins, o_lat, o_lon)
dlat, dlon, dok = coords(dests, d_lat, d_lon)
d_idx = np.flatnonzero(dok)
dlat_v, dlon_v = dlat[d_idx], dlon[d_idx]
kk = min(k, len(d_idx))

COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
o_rows, d_rows, ranks, dists, bearings = [], [], [], [], []
o_valid = np.flatnonzero(ook)
if kk > 0 and len(o_valid):
    chunk = max(1, int(4_000_000 // max(1, len(d_idx))))
    cos_dlat = np.cos(dlat_v)
    for start in range(0, len(o_valid), chunk):
        if start and start % (chunk * 20) == 0:
            omniscope_api.update_message(f"Searched {start:,} of {len(o_valid):,} points")
        oi = o_valid[start:start + chunk]
        la, lo = olat[oi][:, None], olon[oi][:, None]
        a = np.sin((dlat_v - la) / 2) ** 2 + np.cos(la) * cos_dlat * np.sin((dlon_v - lo) / 2) ** 2
        d = 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
        if kk < d.shape[1]:
            part = np.argpartition(d, kk - 1, axis=1)[:, :kk]
        else:
            part = np.tile(np.arange(d.shape[1]), (len(oi), 1))
        pd_ = np.take_along_axis(d, part, axis=1)
        order = np.argsort(pd_, axis=1, kind="stable")
        part = np.take_along_axis(part, order, axis=1)
        pd_ = np.take_along_axis(pd_, order, axis=1)
        for r in range(kk):
            sel = np.ones(len(oi), dtype=bool) if max_dist <= 0 else pd_[:, r] <= max_dist
            if not sel.any():
                continue
            oo, jj = oi[sel], d_idx[part[sel, r]]
            y = np.sin(dlon[jj] - olon[oo]) * np.cos(dlat[jj])
            x = np.cos(olat[oo]) * np.sin(dlat[jj]) - np.sin(olat[oo]) * np.cos(dlat[jj]) * np.cos(dlon[jj] - olon[oo])
            brg = (np.degrees(np.arctan2(y, x)) + 360) % 360
            o_rows.append(oo)
            d_rows.append(jj)
            ranks.append(np.full(len(oo), r + 1))
            dists.append(pd_[sel, r])
            bearings.append(brg)

if o_rows:
    o_rows, d_rows = np.concatenate(o_rows), np.concatenate(d_rows)
    ranks, dists, bearings = np.concatenate(ranks), np.concatenate(dists), np.concatenate(bearings)
    order = np.lexsort((ranks, o_rows))
    o_rows, d_rows, ranks, dists, bearings = (a[order] for a in (o_rows, d_rows, ranks, dists, bearings))
else:
    o_rows = d_rows = ranks = np.array([], dtype=int)
    dists = bearings = np.array([], dtype=float)

if keep_unmatched:
    missing = np.setdiff1d(np.arange(len(origins)), o_rows)
    o_all = np.concatenate([o_rows, missing])
    d_all = np.concatenate([d_rows.astype(float), np.full(len(missing), np.nan)])
    r_all = np.concatenate([ranks.astype(float), np.full(len(missing), np.nan)])
    di_all = np.concatenate([dists, np.full(len(missing), np.nan)])
    b_all = np.concatenate([bearings, np.full(len(missing), np.nan)])
    order = np.lexsort((np.nan_to_num(r_all, nan=1e9), o_all))
    o_all, d_all, r_all, di_all, b_all = (a[order] for a in (o_all, d_all, r_all, di_all, b_all))
else:
    o_all, d_all, r_all, di_all, b_all = o_rows, d_rows.astype(float), ranks.astype(float), dists, bearings

left = origins.iloc[o_all].reset_index(drop=True)
right_idx = [int(j) if np.isfinite(j) else -1 for j in d_all]
right = dests.reindex(right_idx).reset_index(drop=True)
right.columns = [f"Nearest: {c}" for c in right.columns]
right = right.rename(columns={c: c + " (2)" for c in right.columns if c in left.columns})
out = pd.concat([left, right], axis=1)
out["Nearest Rank"] = pd.array(r_all, dtype="Float64").astype("Int64")
out[dist_col] = pd.Series(np.round(di_all, 3), dtype="float64")
out["Bearing (degrees)"] = pd.Series(np.round(b_all, 1), dtype="float64")
out["Direction"] = [COMPASS[int(((b + 22.5) % 360) // 45)] if np.isfinite(b) else None for b in b_all]
status = np.where(np.isfinite(di_all), "Found", np.where(ook[o_all], "None within distance", "Invalid coordinates"))
out["Match Status"] = status

# catchment summary per destination (nearest = rank 1)
first = pd.DataFrame({"d": d_rows[ranks == 1], "dist": dists[ranks == 1]}) if len(ranks) else pd.DataFrame({"d": [], "dist": []})
g = first.groupby("d")["dist"].agg(["size", "mean", "median", "max"]) if len(first) else None
label_field = d_id if d_id else None
summ = pd.DataFrame({"Destination Row": pd.array(np.arange(1, len(dests) + 1), dtype="Int64")})
if label_field:
    summ.insert(0, str(label_field), dests[label_field].to_numpy())
summ["Points Nearest To It"] = pd.array([int(g.loc[j, "size"]) if g is not None and j in g.index else 0 for j in range(len(dests))], dtype="Int64")
for col, key in (("Mean Distance", "mean"), ("Median Distance", "median"), ("Furthest Point", "max")):
    summ[f"{col} ({'km' if unit == 'KM' else 'miles'})"] = pd.Series(
        [round(float(g.loc[j, key]), 3) if g is not None and j in g.index else np.nan for j in range(len(dests))], dtype="float64")
tot = summ["Points Nearest To It"].sum()
summ["Share Of Points"] = pd.Series((summ["Points Nearest To It"].astype(float) / tot) if tot else np.nan, dtype="float64")

omniscope_api.write_output(out, "nearest")
omniscope_api.write_output(summ, "catchments")
n_found = len(np.unique(o_rows))
omniscope_api.close(f"{n_found:,} of {len(origins):,} points matched to {kk} nearest of {len(d_idx):,} destinations"
                    + (f" within {max_dist:g} {unit.lower()}" if max_dist > 0 else "") + ".")
