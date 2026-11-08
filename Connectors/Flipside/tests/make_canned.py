"""Writes an invented Flipside query result in tests/canned/query-result.json, in the shape the Flipside Python SDK
returns (records as dictionaries with a __row_index): daily transactions and active addresses on two chains for
30 days. Run from the block folder: python3 tests/make_canned.py
"""
import datetime as dt
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
rng = random.Random(14)
records = []
for d in range(30):
    day = dt.date(2026, 5, 1) + dt.timedelta(days=d)
    for chain, scale in (("ethereum", 1.0), ("arbitrum", 1.9)):
        tx = int(rng.uniform(1.0e6, 1.35e6) * scale)
        records.append({"block_date": f"{day.isoformat()}T00:00:00.000Z", "chain": chain, "tx_count": tx,
                        "active_addresses": int(tx * rng.uniform(0.28, 0.36)),
                        "avg_fee_usd": round(rng.uniform(0.4, 2.8) / scale, 4), "__row_index": len(records)})
body = {"query_id": "clx9q2ex0001demo", "status": "QUERY_STATE_SUCCESS",
        "columns": ["block_date", "chain", "tx_count", "active_addresses", "avg_fee_usd", "__row_index"],
        "column_types": ["date", "string", "number", "number", "number", "number"], "records": records}
os.makedirs(os.path.join(HERE, "canned"), exist_ok=True)
with open(os.path.join(HERE, "canned", "query-result.json"), "w", encoding="utf-8") as fh:
    json.dump(body, fh, indent=1)
