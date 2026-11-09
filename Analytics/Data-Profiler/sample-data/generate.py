"""Writes customer-orders.csv: 80 invented orders with a few planted data problems.

Run from this folder: python3 generate.py
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
n = 80
dates = pd.Timestamp("2025-01-06") + pd.to_timedelta(np.sort(rng.integers(0, 170, n)), unit="D")
quantity = rng.integers(1, 13, n).astype(float)
price = np.round(rng.uniform(4.5, 59.0, n), 2)
delivery = rng.integers(1, 7, n).astype(float)
discount = rng.choice([0, 0, 0, 5, 10, 15], n).astype(float)
df = pd.DataFrame({
    "Order ID": [f"ORD-{3001 + i}" for i in range(n)],
    "Order Date": dates.strftime("%Y-%m-%d"),
    "Region": rng.choice(["North", "South", "East", "West"], n, p=[0.3, 0.3, 0.2, 0.2]),
    "Channel": rng.choice(["Online", "Store", "Phone"], n, p=[0.55, 0.35, 0.1]),
    "Quantity": quantity,
    "Unit Price": price,
    "Discount %": discount,
    "Delivery Days": delivery,
})
# Planted problems
df.loc[17, "Order ID"] = df.loc[16, "Order ID"]      # a duplicated order number
df.loc[23, "Quantity"] = 120                          # a typing slip: 120 for 12
df.loc[[5, 41, 66], "Region"] = None                  # three orders with no region
df.loc[52, "Order Date"] = None                       # one order with no date
df.loc[[9, 30, 58, 71], "Discount %"] = np.nan        # discount not recorded
df.loc[38, "Delivery Days"] = -3                      # a negative delivery time
df["Order Value"] = np.round(df["Quantity"] * df["Unit Price"] * (1 - df["Discount %"].fillna(0) / 100), 2)
df["Quantity"] = df["Quantity"].astype("Int64")
df["Delivery Days"] = df["Delivery Days"].astype("Int64")
df["Discount %"] = df["Discount %"].astype("Int64")
df.to_csv("customer-orders.csv", index=False)
print(len(df), "orders written")
