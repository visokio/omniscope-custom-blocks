"""Point in Polygon: for each point (latitude / longitude) in the first input,
find the polygon(s) of the second input that contain it, such as the sales
territory, delivery zone, council area or flood zone, and count the points
(and sum a value) per polygon.

Polygons come one per row in the second input, with the geometry in a text
field as GeoJSON (Polygon / MultiPolygon, or a Feature) or WKT (POLYGON /
MULTIPOLYGON). Holes are respected. Pure numpy ray casting with bounding-box
pre-filtering.
"""
import json
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


lat_f, lon_f = opt("lat_field"), opt("lon_field")
geom_f = opt("geometry_field")
value_f = opt("value_field")
mode = opt("match_mode", "FIRST")
keep_unmatched = opt("keep_unmatched", True)

pts = omniscope_api.read_input_records(input_number=0)
polys = omniscope_api.read_input_records(input_number=1)
if pts is None or polys is None:
    omniscope_api.abort("Connect points to input 1 and polygons to input 2.")
for f, df, label in ((lat_f, pts, "latitude"), (lon_f, pts, "longitude"), (geom_f, polys, "geometry")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
for f, df in ((value_f, pts),):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")


# ---------------------------------------------------------- geometry parsing
def parse_wkt(s):
    s = s.strip()
    m = re.match(r"^(MULTIPOLYGON|POLYGON)\s*(Z|M|ZM)?\s*\((.*)\)\s*$", s, re.I | re.S)
    if not m:
        raise ValueError("not a POLYGON / MULTIPOLYGON")
    body = m.group(3)

    def rings_of(poly_txt):
        return [[tuple(float(v) for v in pt.split()[:2]) for pt in ring.split(",")] for ring in re.findall(r"\(([^()]+)\)", poly_txt)]
    if m.group(1).upper() == "POLYGON":
        return [rings_of(body)]
    polys_txt = re.findall(r"\(\s*(\([^()]+\)(?:\s*,\s*\([^()]+\))*)\s*\)", body)
    return [rings_of(p) for p in polys_txt]


def parse_geom(v):
    """Returns a list of polygons, each a list of rings of (lon, lat)."""
    if v is None or (isinstance(v, float) and v != v):
        raise ValueError("empty geometry")
    s = str(v).strip()
    if s.startswith("{"):
        g = json.loads(s)
        if g.get("type") == "Feature":
            g = g.get("geometry") or {}
        if g.get("type") == "FeatureCollection":
            raise ValueError("one geometry per row expected (got a FeatureCollection)")
        if g.get("type") == "Polygon":
            return [[[tuple(p[:2]) for p in ring] for ring in g["coordinates"]]]
        if g.get("type") == "MultiPolygon":
            return [[[tuple(p[:2]) for p in ring] for ring in poly] for poly in g["coordinates"]]
        raise ValueError(f"unsupported GeoJSON type {g.get('type')}")
    return parse_wkt(s)


geoms, bad = [], []
for i, v in enumerate(polys[geom_f].tolist()):
    try:
        rings = [np.asarray(r, dtype=float) for poly in parse_geom(v) for r in poly]
        rings = [r for r in rings if len(r) >= 3]
        if not rings:
            raise ValueError("no rings")
        allpts = np.vstack(rings)
        geoms.append((i, rings, allpts[:, 0].min(), allpts[:, 0].max(), allpts[:, 1].min(), allpts[:, 1].max()))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        bad.append((i, str(e)))
if bad and not geoms:
    omniscope_api.abort(f"No polygon could be read; first problem (row {bad[0][0] + 1}): {bad[0][1]}")

lat = pd.to_numeric(pts[lat_f], errors="coerce").to_numpy(dtype=float)
lon = pd.to_numeric(pts[lon_f], errors="coerce").to_numpy(dtype=float)
valid = np.isfinite(lat) & np.isfinite(lon)


def inside(x, y, rings):
    """Even-odd rule over all rings (so holes work)."""
    res = np.zeros(len(x), dtype=bool)
    for r in rings:
        xs, ys = r[:, 0], r[:, 1]
        xj, yj = np.roll(xs, 1), np.roll(ys, 1)
        for k in range(len(xs)):
            cond = (ys[k] > y) != (yj[k] > y)
            with np.errstate(divide="ignore", invalid="ignore"):
                xint = (xj[k] - xs[k]) * (y - ys[k]) / (yj[k] - ys[k]) + xs[k]
            res ^= cond & (x < xint)
    return res


matches = []  # (point index, polygon row)
for pi, rings, x0, x1, y0, y1 in geoms:
    cand = np.flatnonzero(valid & (lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1))
    if len(cand):
        hit = inside(lon[cand], lat[cand], rings)
        matches.extend((int(j), pi) for j in cand[hit])
matches.sort()
count = pd.Series([j for j, _ in matches]).value_counts() if matches else pd.Series(dtype=int)  # before keeping first only
if mode == "FIRST":
    seen, first = set(), []
    for j, pi in matches:
        if j not in seen:
            seen.add(j)
            first.append((j, pi))
    matches = first

m_pts = [j for j, _ in matches]
m_pol = [pi for _, pi in matches]
if keep_unmatched:
    matched_set = set(m_pts)
    un = [j for j in range(len(pts)) if j not in matched_set]
    m_pts += un
    m_pol += [None] * len(un)
order = np.argsort(np.array(m_pts, dtype=int), kind="stable") if m_pts else np.array([], dtype=int)
m_pts = [m_pts[k] for k in order]
m_pol = [m_pol[k] for k in order]

left = pts.iloc[m_pts].reset_index(drop=True)
keep_cols = [c for c in polys.columns if c != geom_f]
right = polys[keep_cols].reindex([p if p is not None else -1 for p in m_pol]).reset_index(drop=True)
right.columns = [f"Polygon: {c}" for c in right.columns]
right = right.rename(columns={c: c + " (2)" for c in right.columns if c in left.columns})
out = pd.concat([left, right], axis=1)
out["Polygon Row"] = pd.array([p + 1 if p is not None else None for p in m_pol], dtype="Int64")
cnt_map = count.to_dict()
out["Polygons Containing Point"] = pd.array([int(cnt_map.get(j, 0)) for j in m_pts], dtype="Int64")
out["Match Status"] = ["Inside" if p is not None else ("Invalid coordinates" if not valid[j] else "Outside all polygons")
                       for j, p in zip(m_pts, m_pol)]

hits = pd.DataFrame({"pol": [p for p in m_pol if p is not None], "pt": [j for j, p in zip(m_pts, m_pol) if p is not None]})
summ = polys[keep_cols].copy()
summ.insert(0, "Polygon Row", pd.array(np.arange(1, len(polys) + 1), dtype="Int64"))
cnt = hits.groupby("pol").size() if len(hits) else pd.Series(dtype=int)
summ["Points"] = pd.array([int(cnt.get(i, 0)) for i in range(len(polys))], dtype="Int64")
if value_f:
    vals = pd.to_numeric(pts[value_f], errors="coerce").fillna(0.0).to_numpy(dtype=float)
    sums = hits.assign(v=vals[hits["pt"].to_numpy(dtype=int)] if len(hits) else []).groupby("pol")["v"].sum() if len(hits) else pd.Series(dtype=float)
    summ[f"Total {value_f}"] = pd.Series([float(sums.get(i, 0.0)) for i in range(len(polys))], dtype="float64")
summ["Geometry Status"] = ["Could not read: " + dict(bad)[i] if i in dict(bad) else "OK" for i in range(len(polys))]

omniscope_api.write_output(out, "points")
omniscope_api.write_output(summ, "polygons")
n_in = len(set(j for j, p in zip(m_pts, m_pol) if p is not None))
omniscope_api.close(f"{n_in:,} of {len(pts):,} points inside {len(geoms):,} polygons"
                    + (f"; {len(bad)} polygon(s) could not be read." if bad else "."))
