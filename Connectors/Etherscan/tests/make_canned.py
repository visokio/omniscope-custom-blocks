"""Writes the invented Etherscan API responses in tests/canned/ and the sample input sample-data/addresses.csv.
The addresses are random, made up for the tests. Run from the block folder: python3 tests/make_canned.py
"""
import csv
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.dirname(HERE)
OUT = os.path.join(HERE, "canned")
rng = random.Random(11)


def address():
    return "0x" + "".join(rng.choice("0123456789abcdef") for _ in range(40))


def tx_hash():
    return "0x" + "".join(rng.choice("0123456789abcdef") for _ in range(64))


wallets = [("Treasury", 31), ("Payroll", 24), ("Grants", 12), ("Event tickets", 0), ("Cold storage", 3)]
accounts = [(name, address(), n) for name, n in wallets]
others = [address() for _ in range(15)]

balances = {"status": "1", "message": "OK", "result": []}
for i, (name, a, _) in enumerate(accounts):
    wei = [184250000000000000000, 12750330000000000000, 4100000000000000000, 0, 902500000000000000000][i]
    balances["result"].append({"account": a, "balance": str(wei)})

block, ts = 21550000, 1735700000  # early January 2025
os.makedirs(OUT, exist_ok=True)
for name, a, n in accounts:
    txs = []
    b, t = block, ts
    for k in range(n):
        b += rng.randint(2000, 60000)
        t += rng.randint(20000, 700000)
        incoming = rng.random() < 0.45
        counterparty = rng.choice(others)
        value = rng.choice([0, rng.randint(1, 400) * 10 ** 16, rng.randint(1, 50) * 10 ** 17])
        failed = rng.random() < 0.05
        txs.append({
            "blockNumber": str(b), "timeStamp": str(t), "hash": tx_hash(), "nonce": str(k),
            "blockHash": tx_hash(), "transactionIndex": str(rng.randint(0, 220)),
            "from": counterparty if incoming else a, "to": a if incoming else counterparty,
            "value": str(value), "gas": "21000" if value else "65000",
            "gasPrice": str(rng.randint(800000000, 30000000000)), "isError": "1" if failed else "0",
            "txreceipt_status": "0" if failed else "1", "input": "0x" if value else "0xa9059cbb",
            "contractAddress": "", "cumulativeGasUsed": str(rng.randint(100000, 29000000)),
            "gasUsed": "21000" if value else str(rng.randint(30000, 64000)), "confirmations": str(23660000 - b),
            "methodId": "0x" if value else "0xa9059cbb", "functionName": "" if value else
            "transfer(address _to, uint256 _value)",
        })
    body = {"status": "1", "message": "OK", "result": txs} if txs else \
        {"status": "0", "message": "No transactions found", "result": []}
    with open(os.path.join(OUT, f"txlist-{a}.json"), "w", encoding="utf-8") as fh:
        json.dump(body, fh, indent=1)

with open(os.path.join(OUT, "balancemulti.json"), "w", encoding="utf-8") as fh:
    json.dump(balances, fh, indent=1)

os.makedirs(os.path.join(BLOCK, "sample-data"), exist_ok=True)
with open(os.path.join(BLOCK, "sample-data", "addresses.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["Wallet", "Address"])
    for name, a, _ in accounts:
        w.writerow([name, a])
