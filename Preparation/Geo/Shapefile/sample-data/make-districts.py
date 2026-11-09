"""Writes districts.geojson and districts.csv (the same shapes as WKT text): four invented districts (made-up names and shapes, not real boundaries).

Brackenford is L-shaped (its centroid falls outside it); Dunmere has a detached second part.
Run: python3 make-districts.py (needs shapely for the WKT)
"""
import json

def ring(*pts):
    pts = [list(p) for p in pts]
    return pts + [pts[0]]

features = [
    ("D01", "Ashcombe", 4200, {"type": "Polygon", "coordinates": [ring(
        (-1.60, 53.12), (-1.40, 53.12), (-1.40, 53.16), (-1.26, 53.16), (-1.26, 53.24), (-1.60, 53.24))]}),
    ("D02", "Brackenford", 2900, {"type": "Polygon", "coordinates": [ring(
        (-1.40, 53.12), (-1.20, 53.12), (-1.20, 53.24), (-1.26, 53.24), (-1.26, 53.16), (-1.40, 53.16))]}),
    ("D03", "Coldharbour Vale", 3600, {"type": "Polygon", "coordinates": [ring(
        (-1.60, 53.00), (-1.35, 53.00), (-1.35, 53.12), (-1.60, 53.12))]}),
    ("D04", "Dunmere", 1800, {"type": "MultiPolygon", "coordinates": [
        [ring((-1.35, 53.00), (-1.20, 53.00), (-1.20, 53.12), (-1.35, 53.12))],
        [ring((-1.10, 53.05), (-1.06, 53.05), (-1.06, 53.08), (-1.10, 53.08))]]}),
]

fc = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"district_code": c, "district_name": n, "households": h}, "geometry": g}
    for c, n, h, g in features]}

with open("districts.geojson", "w", encoding="utf-8") as fh:
    json.dump(fc, fh, indent=1)
    fh.write("\n")

from shapely.geometry import shape  # noqa: E402
import csv  # noqa: E402

with open("districts.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["District code", "District name", "Households", "Boundary"])
    for c, n, h, g in features:
        w.writerow([c, n, h, shape(g).wkt])
