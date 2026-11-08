"""Writes tests/canned/monthly-sales.csv, the invented file the tests' stand-in GitHub serves.

Run from the block folder: python3 tests/make_canned.py
"""

import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(11)
regions = ["North", "Midlands", "South East", "South West", "Scotland", "Wales"]
rows = []
for month in ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"]:
    for region in regions:
        orders = rng.randint(80, 400)
        rows.append([month, region, orders, f"{orders * rng.uniform(38, 62):.2f}"])
os.makedirs(os.path.join(HERE, "canned"), exist_ok=True)
with open(os.path.join(HERE, "canned", "monthly-sales.csv"), "w", newline="", encoding="utf-8") as fh:
    writer = csv.writer(fh)
    writer.writerow(["Month", "Region", "Orders", "Revenue"])
    writer.writerows(rows)
print(len(rows), "records")
