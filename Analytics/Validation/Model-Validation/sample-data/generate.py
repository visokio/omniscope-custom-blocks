"""Writes ticket-predictions.csv: 120 invented support tickets with the team a model predicted and the team
that actually handled them.

Run from this folder: python3 generate.py
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(5)
teams = ["Billing", "Technical", "Account", "Delivery", "Complaints"]
counts = {"Billing": 34, "Technical": 40, "Account": 22, "Delivery": 20, "Complaints": 4}
# How often a ticket of each actual team is predicted as each team (rows: actual). The model was trained
# before the Complaints team existed, so it never predicts it.
mix = {
    "Billing":    [0.85, 0.03, 0.09, 0.03, 0.0],
    "Technical":  [0.03, 0.90, 0.05, 0.02, 0.0],
    "Account":    [0.18, 0.09, 0.73, 0.0, 0.0],
    "Delivery":   [0.05, 0.0, 0.0, 0.95, 0.0],
    "Complaints": [0.25, 0.0, 0.25, 0.5, 0.0],
}
rows = []
for actual, k in counts.items():
    predicted = rng.choice(teams, k, p=mix[actual])
    rows += [(actual, p) for p in predicted]
df = pd.DataFrame(rows, columns=["Actual Team", "Predicted Team"]).sample(frac=1, random_state=3).reset_index(drop=True)
df.insert(0, "Ticket", [f"T-{5001 + i}" for i in range(len(df))])
df.insert(1, "Opened", pd.Timestamp("2025-05-01") + pd.to_timedelta(np.sort(rng.integers(0, 30, len(df))), unit="D"))
df["Opened"] = df["Opened"].dt.strftime("%Y-%m-%d")
df.loc[[17, 88], "Predicted Team"] = None  # the model gave no answer for two tickets
df.to_csv("ticket-predictions.csv", index=False)
print(len(df), "tickets")
