"""Writes pump-history.csv (150 inspected pumps with their condition) and pump-readings.csv (30 pumps to assess).

Run from this folder: python3 generate.py
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(11)
PROFILES = {  # vibration mm/s, temperature C, pressure bar, runtime hours range
    "Normal": ((2.0, 0.6), (60, 5), (5.0, 0.5), (500, 8000)),
    "Worn": ((5.0, 0.8), (70, 5), (4.3, 0.5), (6000, 16000)),
    "Faulty": ((8.5, 1.2), (84, 5), (3.2, 0.6), (4000, 18000)),
}


def pumps(counts, first_id):
    rows = []
    for cond, k in counts.items():
        (vm, vs), (tm, ts), (pm, ps), (r0, r1) = PROFILES[cond]
        for _ in range(k):
            rows.append({"Vibration": round(max(0.3, rng.normal(vm, vs)), 2),
                         "Temperature": round(rng.normal(tm, ts), 1),
                         "Pressure": round(max(0.5, rng.normal(pm, ps)), 2),
                         "Runtime Hours": int(rng.integers(r0, r1)),
                         "Condition": cond})
    df = pd.DataFrame(rows).sample(frac=1, random_state=int(rng.integers(1e6))).reset_index(drop=True)
    df.insert(0, "Pump", [f"P-{first_id + i}" for i in range(len(df))])
    df.insert(1, "Site", rng.choice(["Riverside", "Hillcrest", "Docklands"], len(df)))
    return df


history = pumps({"Normal": 80, "Worn": 45, "Faulty": 25}, 1001)
history.to_csv("pump-history.csv", index=False)

new = pumps({"Normal": 16, "Worn": 9, "Faulty": 5}, 2001)
new.loc[7, "Vibration"] = np.nan  # a sensor that did not report
new.drop(columns="Condition").to_csv("pump-readings.csv", index=False)
new[["Pump", "Condition"]].to_csv("pump-readings-inspected.csv", index=False)  # what an engineer found later
print(len(history), "history,", len(new), "new")
