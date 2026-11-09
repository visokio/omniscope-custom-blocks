"""Trade Area Summary: for each site (store, branch, depot, clinic), how many
points (customers, households, competitors, incidents) lie within each of
several radii, how much value they carry, and how much of that is shared with
other sites, using great-circle (haversine) distances.

Per site and radius: points and value within, share of all points, points
that no other site reaches within the same radius (exclusive), and the average
distance. Per point: nearest site and its distance, the distance band, and how
many sites reach it within the largest radius.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


s_id, s_lat, s_lon = opt("site_field"), opt("site_lat"), opt("site_lon")
p_lat, p_lon, p_val, p_id = opt("point_lat"), opt("point_lon"), opt("point_value"), opt("point_id")
radii_txt = opt("radii", "1, 3, 5, 10")
unit = opt("unit", "KM")
R_EARTH = 6371.0088 if unit == "KM" else 3958.7613

S = omniscope_api.read_input_records(input_number=0)
P = omniscope_api.read_input_records(input_number=1)
if S is None or P is None:
    omniscope_api.abort("Connect the sites to input 1 and the points (customers, households...) to input 2.")
for df, f, lab in ((S, s_id, "site name"), (S, s_lat, "site latitude"), (S, s_lon, "site longitude"), (P, p_lat, "point latitude"), (P, p_lon, "point longitude")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
for f in (p_val, p_id):
    if f and f not in P.columns:
        omniscope_api.abort(f"Field '{f}' is not in input 2.")
try:
    radii = sorted({float(x) for x in re.split(r"[,;\s]+", radii_txt) if x.strip()})
except ValueError:
    omniscope_api.abort("Radii must be numbers, for example: 1, 3, 5, 10")
if not radii or radii[0] <= 0:
    omniscope_api.abort("Give at least one radius above zero.")


def coords(df, la, lo):
    a = pd.to_numeric(df[la], errors="coerce").astype("float64").to_numpy()
    b = pd.to_numeric(df[lo], errors="coerce").astype("float64").to_numpy()
    ok = ~np.isnan(a) & ~np.isnan(b) & (np.abs(a) <= 90) & (np.abs(b) <= 180)
    return a, b, ok


sla, slo, sok = coords(S, s_lat, s_lon)
pla, plo, pok = coords(P, p_lat, p_lon)
names = S[s_id].astype(object).where(S[s_id].notna(), "(blank)").map(str).to_numpy()
val = pd.to_numeric(P[p_val], errors="coerce").fillna(0).astype("float64").to_numpy() if p_val else np.ones(len(P))
si = np.nonzero(sok)[0]
pi = np.nonzero(pok)[0]
ns, npnt = len(si), len(pi)
rmax = radii[-1]
nearest = np.full(len(P), -1)
nd = np.full(len(P), np.nan)
reach = np.zeros(len(P), dtype=int)
cnt = np.zeros((ns, len(radii)))
vsum = np.zeros((ns, len(radii)))
dsum = np.zeros((ns, len(radii)))
excl = np.zeros((ns, len(radii)))
lat1, lon1 = np.radians(sla[si]), np.radians(slo[si])
CH = max(1, 2_000_000 // max(ns, 1))
for c0 in range(0, npnt, CH):
    idx = pi[c0:c0 + CH]
    lat2, lon2 = np.radians(pla[idx]), np.radians(plo[idx])
    dlat = lat2[None, :] - lat1[:, None]
    dlon = lon2[None, :] - lon1[:, None]
    h = np.sin(dlat / 2) ** 2 + np.cos(lat1)[:, None] * np.cos(lat2)[None, :] * np.sin(dlon / 2) ** 2
    D = 2 * R_EARTH * np.arcsin(np.sqrt(np.clip(h, 0, 1)))        # sites x points
    if ns:
        k = np.argmin(D, axis=0)
        nearest[idx] = si[k]
        nd[idx] = D[k, np.arange(len(idx))]
        reach[idx] = (D <= rmax).sum(axis=0)
    for j, r in enumerate(radii):
        within = D <= r
        nwithin = within.sum(axis=0)
        cnt[:, j] += within.sum(axis=1)
        vsum[:, j] += within @ val[idx]
        dsum[:, j] += (D * within).sum(axis=1)
        excl[:, j] += (within & (nwithin == 1)[None, :]).sum(axis=1)

total_pts, total_val = npnt, float(val[pi].sum())
rows = []
for a, s in enumerate(si):
    for j, r in enumerate(radii):
        rows.append({str(s_id): names[s], "Radius": r, "Unit": unit.lower(), "Points Within": int(cnt[a, j]), "Value Within": float(vsum[a, j]),
                     "Share Of All Points": cnt[a, j] / total_pts if total_pts else np.nan, "Share Of All Value": vsum[a, j] / total_val if total_val else np.nan,
                     "Exclusive Points": int(excl[a, j]), "Shared Points": int(cnt[a, j] - excl[a, j]),
                     "Average Distance": dsum[a, j] / cnt[a, j] if cnt[a, j] else np.nan})
summ = pd.DataFrame(rows, columns=[str(s_id), "Radius", "Unit", "Points Within", "Value Within", "Share Of All Points", "Share Of All Value", "Exclusive Points",
                                   "Shared Points", "Average Distance"])
for c in ("Points Within", "Exclusive Points", "Shared Points"):
    summ[c] = summ[c].astype("int64")
for c in ("Radius", "Value Within", "Share Of All Points", "Share Of All Value", "Average Distance"):
    summ[c] = summ[c].astype("float64")
if not p_val:
    summ = summ.drop(columns=["Value Within", "Share Of All Value"])

pts = P.copy()
pts["Nearest Site"] = [names[k] if k >= 0 else None for k in nearest]
pts["Distance To Nearest Site"] = nd.astype("float64")
edges = [0.0] + radii


def band(d):
    if d != d:
        return None
    for lo, hi in zip(edges[:-1], edges[1:]):
        if d <= hi:
            return f"{lo:g}-{hi:g} {unit.lower()}"
    return f"Over {rmax:g} {unit.lower()}"


pts["Distance Band"] = [band(d) for d in nd]
pts["Sites Within Largest Radius"] = reach.astype("int64")
pts["Valid Coordinates"] = np.where(pok, "Yes", "No")
omniscope_api.write_output(summ, "sites")
omniscope_api.write_output(pts, "points")
outside = int(((nd > rmax) | np.isnan(nd)).sum())
omniscope_api.close(f"{ns} sites, {npnt:,} points with valid coordinates; {npnt - int((nd > rmax).sum()):,} within {rmax:g} {unit.lower()} of a site"
                    + (f"; {int((~pok).sum()):,} points and {int((~sok).sum()):,} sites without valid coordinates" if (~pok).any() or (~sok).any() else "") + ".")
