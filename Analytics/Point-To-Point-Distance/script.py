"""Point-to-Point Distance: for each row, the great-circle distance between two
locations (from and to latitude / longitude): journeys, deliveries, patient
travel, customer to store, with the initial compass bearing, the midpoint and
an optional estimated road distance and travel time from simple factors.

Haversine formula on a spherical Earth (mean radius 6,371 km), accurate to
about 0.5% for most purposes. Rows with missing or impossible coordinates are
kept and marked.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


f_lat, f_lon, t_lat, t_lon = opt("from_lat"), opt("from_lon"), opt("to_lat"), opt("to_lon")
unit = opt("unit", "KM")
road = float(opt("road_factor", 0) or 0)
speed = float(opt("speed", 0) or 0)
R = 6371.0088 if unit == "KM" else 3958.7613
U = unit.lower()

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
for f, lab in ((f_lat, "from latitude"), (f_lon, "from longitude"), (t_lat, "to latitude"), (t_lon, "to longitude")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
num = lambda f: pd.to_numeric(df[f], errors="coerce").astype("float64").to_numpy()
la1, lo1, la2, lo2 = num(f_lat), num(f_lon), num(t_lat), num(t_lon)
ok = ~(np.isnan(la1) | np.isnan(lo1) | np.isnan(la2) | np.isnan(lo2)) & (np.abs(la1) <= 90) & (np.abs(la2) <= 90) & (np.abs(lo1) <= 180) & (np.abs(lo2) <= 180)
p1, p2, l1, l2 = np.radians(la1), np.radians(la2), np.radians(lo1), np.radians(lo2)
dp, dl = p2 - p1, l2 - l1
h = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
dist = 2 * R * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
brg = (np.degrees(np.arctan2(np.sin(dl) * np.cos(p2), np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dl))) + 360) % 360
bx, by = np.cos(p2) * np.cos(dl), np.cos(p2) * np.sin(dl)
mlat = np.degrees(np.arctan2(np.sin(p1) + np.sin(p2), np.sqrt((np.cos(p1) + bx) ** 2 + by ** 2)))
mlon = (np.degrees(l1 + np.arctan2(by, np.cos(p1) + bx)) + 540) % 360 - 180
POINTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
out = df.copy()
out[f"Distance ({U})"] = np.where(ok, dist, np.nan)
out["Bearing (degrees)"] = np.where(ok & (dist > 0), brg, np.nan)
out["Direction"] = [POINTS[int(((b + 22.5) % 360) // 45)] if b == b else None for b in out["Bearing (degrees)"]]
out["Midpoint Latitude"] = np.where(ok, mlat, np.nan)
out["Midpoint Longitude"] = np.where(ok, mlon, np.nan)
if road > 0:
    out[f"Estimated Road Distance ({U})"] = out[f"Distance ({U})"] * road
    if speed > 0:
        out["Estimated Minutes"] = out[f"Estimated Road Distance ({U})"] / speed * 60
out["Valid Coordinates"] = np.where(ok, "Yes", "No")
for c in out.columns[len(df.columns):]:
    if c not in ("Direction", "Valid Coordinates"):
        out[c] = out[c].astype("float64")
omniscope_api.write_output(out, "distances")
d = out[f"Distance ({U})"]
omniscope_api.close(f"{int(ok.sum()):,} of {len(out):,} rows measured; median {d.median():,.1f} {U}, total {d.sum():,.0f} {U}" + (f"; {int((~ok).sum()):,} rows without valid coordinates" if (~ok).any() else "") + ".")
