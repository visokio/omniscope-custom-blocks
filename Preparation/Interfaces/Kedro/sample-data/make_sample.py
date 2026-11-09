"""Writes the invented sample data: 40 orders from a stationery wholesaler and a sales target per region."""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7)
products = {"A4 paper (box)": 21.50, "Ballpoint pens (50)": 9.80, "Lever-arch file": 3.20,
            "Desk stapler": 12.40, "Sticky notes (12)": 7.60, "Whiteboard markers (8)": 11.90}
regions = ["North", "Midlands", "South East", "South West", "Wales"]
rows = []
for i in range(40):
    product = rng.choice(list(products))
    rows.append({
        "Order": f"ORD-{3101 + i}",
        "Order Date": (pd.Timestamp("2025-04-01") + pd.Timedelta(days=int(rng.integers(0, 30)))).date().isoformat(),
        "Region": regions[i % len(regions)] if i % 7 else rng.choice(regions),
        "Product": product,
        "Quantity": int(rng.integers(1, 25)),
        "Unit Price": products[product],
        "Status": rng.choice(["Shipped", "Shipped", "Shipped", "Pending", "Cancelled"]),
    })
pd.DataFrame(rows).to_csv(os.path.join(HERE, "orders.csv"), index=False)
pd.DataFrame({"Region": regions, "Target": [800, 600, 900, 1500, 500]}).to_csv(
    os.path.join(HERE, "region-targets.csv"), index=False)
