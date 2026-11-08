"""Writes invented daily price histories in tests/canned/<ticker>.csv, as yfinance returns them (index Date in the
exchange's time zone), and the sample input sample-data/holdings.csv. The companies and tickers are fictional
and the prices invented. Run from the block folder: python3 tests/make_canned.py
"""
import csv
import os
import random

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.dirname(HERE)
rng = random.Random(21)

# ticker, exchange time zone, starting close, daily volatility, typical volume, dividend (date, amount)
listings = [("QLMK", "America/New_York", 84.20, 0.014, 2_400_000, None),
            ("HLDW.L", "Europe/London", 412.5, 0.011, 5_800_000, ("2026-08-13", 9.8)),
            ("LGRW.DE", "Europe/Berlin", 57.36, 0.016, 910_000, None)]
# Each exchange's own weekday closures in July to September 2026: New York shuts for Independence Day (observed
# Friday 3 July) and Labor Day (7 September), London for the summer bank holiday (31 August); Frankfurt trades
# every weekday. The bars for those days are generated and then dropped, so the other days' prices stay the same.
closed = {"QLMK": ["2026-07-03", "2026-09-07"], "HLDW.L": ["2026-08-31"], "LGRW.DE": []}
os.makedirs(os.path.join(HERE, "canned"), exist_ok=True)
for ticker, tz, close, vol, volume, dividend in listings:
    days = pd.bdate_range("2026-07-01", "2026-09-30")
    rows = []
    for d in days:
        open_ = round(close * (1 + rng.gauss(0, vol / 3)), 2)
        close = round(open_ * (1 + rng.gauss(0.0004, vol)), 2)
        high = round(max(open_, close) * (1 + abs(rng.gauss(0, vol / 2))), 2)
        low = round(min(open_, close) * (1 - abs(rng.gauss(0, vol / 2))), 2)
        div = dividend[1] if dividend and d == pd.Timestamp(dividend[0]) else 0.0
        rows.append({"Date": d.tz_localize(tz), "Open": open_, "High": high, "Low": low, "Close": close,
                     "Volume": int(volume * rng.uniform(0.6, 1.5)), "Dividends": div, "Stock Splits": 0.0})
    rows = [r for r in rows if r["Date"].strftime("%Y-%m-%d") not in closed[ticker]]
    pd.DataFrame(rows).to_csv(os.path.join(HERE, "canned", f"{ticker}.csv"), index=False)

os.makedirs(os.path.join(BLOCK, "sample-data"), exist_ok=True)
with open(os.path.join(BLOCK, "sample-data", "holdings.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["Holding", "Account", "Ticker", "Company", "Shares"])
    w.writerows([["H-1", "Pension", "QLMK", "Quillmark Instruments", 120],
                 ["H-2", "Pension", "HLDW.L", "Hollindrew Foods", 2500],
                 ["H-3", "Pension", "LGRW.DE", "Lindgrau Werke", 300],
                 ["H-4", "Savings", "QLMK", "Quillmark Instruments", 40],
                 ["H-5", "Savings", "MRBY", "Marrowby Shipping", 75]])
