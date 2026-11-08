"""Writes the invented Dune API result in tests/canned/results.json: an invented query (id 4100217, "daily DEX
trades by chain") with 30 days x 4 chains. The tests page through it and build the status answers themselves.
Run from the block folder: python3 tests/make_canned.py
"""
import datetime as dt
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(3)

chains = [("ethereum", 1.0), ("arbitrum", 0.7), ("base", 0.9), ("polygon", 0.35)]
pairs = ["WETH-USDC", "WETH-USDT", "WBTC-WETH", "USDC-USDT"]
rows = []
day0 = dt.date(2026, 9, 1)
for d in range(30):
    day = day0 + dt.timedelta(days=d)
    weekend = day.weekday() >= 5
    for chain, scale in chains:
        trades = int(rng.uniform(80000, 140000) * scale * (0.75 if weekend else 1))
        volume = round(trades * rng.uniform(1800, 3200), 2)
        rows.append({
            "day": f"{day.isoformat()} 00:00:00.000 UTC",
            "chain": chain,
            "trades": trades,
            "volume_usd": volume,
            "is_weekend": weekend,
            "top_pair": rng.choice(pairs[:3]) if chain != "polygon" else rng.choice(pairs),
            "largest_trade_wei": str(rng.randint(10 ** 21, 9 * 10 ** 22)),
            "venues": rng.sample(["uniswap", "curve", "balancer", "sushiswap", "aerodrome"], 2),
        })
# one day's polygon volume is missing (the query's join found no prices)
rows[-1]["volume_usd"] = None

columns = ["day", "chain", "trades", "volume_usd", "is_weekend", "top_pair", "largest_trade_wei", "venues"]
types = ["timestamp(3) with time zone", "varchar", "bigint", "double", "boolean", "varchar", "uint256",
         "array(varchar)"]
body = {
    "execution_id": "01K9ZQ4T7W2R8M5H3XJ6D1VYCE",
    "query_id": 4100217,
    "is_execution_finished": True,
    "state": "QUERY_STATE_COMPLETED",
    "submitted_at": "2026-10-01T06:00:02.114Z",
    "expires_at": "2026-12-30T06:00:41.906Z",
    "execution_started_at": "2026-10-01T06:00:02.530Z",
    "execution_ended_at": "2026-10-01T06:00:41.906Z",
    "result": {
        "rows": rows,
        "metadata": {"column_names": columns, "column_types": types, "row_count": len(rows),
                     "total_row_count": len(rows), "result_set_bytes": 23110, "total_result_set_bytes": 23110,
                     "datapoint_count": len(rows) * len(columns), "pending_time_millis": 416,
                     "execution_time_millis": 39376},
        "update_type": "append",
    },
}
os.makedirs(os.path.join(HERE, "canned"), exist_ok=True)
with open(os.path.join(HERE, "canned", "results.json"), "w", encoding="utf-8") as fh:
    json.dump(body, fh, indent=1)
