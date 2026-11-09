"""Writes the invented Overpass API data in tests/canned/ways.json (every street way the fake server knows,
in Overpass JSON with `out geom`) and the sample input sample-data/deliveries.csv.
The geometry is invented. Run from the block folder: python3 tests/make_canned.py
"""
import csv
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.dirname(HERE)
rng = random.Random(5)

# (name, points, highway type); None name = an unnamed way. The last one is a building, not a street.
ways = [("High Street", 5, "primary"), ("High Street", 4, "primary"), ("High Street North", 3, "secondary"),
        ("Station Road", 7, "secondary"), ("Church Lane", 4, "residential"), ("Mill Street", 3, "residential"),
        ("Mill Street", 3, "residential"), ("Park Avenue", 5, "residential"), ("Highfield Road", 3, "residential"),
        (None, 4, "service")]
elements = []
way_id, node_id = 40021500, 3110400000
for name, n, highway in ways:
    lat, lon = 53.78 + rng.random() * 0.04, -1.57 + rng.random() * 0.06
    dlat, dlon = rng.uniform(-0.0012, 0.0012), rng.uniform(-0.0015, 0.0015)
    geometry, nodes = [], []
    for i in range(n):
        geometry.append({"lat": round(lat + i * dlat + rng.uniform(-0.0001, 0.0001), 7),
                         "lon": round(lon + i * dlon + rng.uniform(-0.0001, 0.0001), 7)})
        node_id += rng.randint(1, 900)
        nodes.append(node_id)
    tags = {"highway": highway}
    if name:
        tags["name"] = name
    way_id += rng.randint(10, 50000)
    lats, lons = [g["lat"] for g in geometry], [g["lon"] for g in geometry]
    elements.append({"type": "way", "id": way_id,
                     "bounds": {"minlat": min(lats), "minlon": min(lons), "maxlat": max(lats), "maxlon": max(lons)},
                     "nodes": nodes, "geometry": geometry, "tags": tags})
# A building whose name contains a street name: not a street, so never returned
elements.append({"type": "way", "id": 912000777, "nodes": [1, 2, 3, 4, 1],
                 "geometry": [{"lat": 53.8001, "lon": -1.5501}, {"lat": 53.8002, "lon": -1.5501},
                              {"lat": 53.8002, "lon": -1.5499}, {"lat": 53.8001, "lon": -1.5499},
                              {"lat": 53.8001, "lon": -1.5501}],
                 "tags": {"building": "yes", "name": "High Street Surgery"}})

os.makedirs(os.path.join(HERE, "canned"), exist_ok=True)
with open(os.path.join(HERE, "canned", "ways.json"), "w", encoding="utf-8") as fh:
    json.dump({"version": 0.6, "generator": "Overpass API (invented test data)",
               "osm3s": {"copyright": "Invented test data in the shape of an Overpass API answer."},
               "elements": elements}, fh, indent=1)

os.makedirs(os.path.join(BLOCK, "sample-data"), exist_ok=True)
deliveries = [("D-101", "High Street"), ("D-102", "Station Road"), ("D-103", "Church Lane"), ("D-104", "High Street"),
              ("D-105", "Mill Street"), ("D-106", "Park Avenue"), ("D-107", "Kingfisher Way"), ("D-108", "")]
with open(os.path.join(BLOCK, "sample-data", "deliveries.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["Delivery", "Street"])
    w.writerows(deliveries)
