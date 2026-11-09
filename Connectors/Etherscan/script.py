"""Etherscan connector: native-coin balances, or the normal transactions, of the addresses in a field,
from the Etherscan API V2 (https://docs.etherscan.io), which serves Ethereum and other chains by chain id."""
import re
import time

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

API_URL = "https://api.etherscan.io/v2/api"
TIMEOUT = 60
BALANCE_BATCH = 20        # balancemulti takes up to 20 addresses per call
TX_PAGE = 10000           # txlist returns at most 10,000 transactions per call (page x offset <= 10,000)
PAUSE = 0.35              # the free plan allows 3 calls a second
WEI = 10 ** 18
ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")

BALANCE_COLUMNS = ["Account", "Balance", "Balance (wei)"]
# txlist fields in output order, and how each is typed (every value arrives as text)
TX_FIELDS = [
    ("blockNumber", "int"), ("timeStamp", "int"), ("hash", "text"), ("nonce", "int"), ("blockHash", "text"),
    ("transactionIndex", "int"), ("from", "text"), ("to", "text"), ("value", "text"), ("gas", "int"),
    ("gasPrice", "int"), ("isError", "int"), ("txreceipt_status", "int"), ("input", "text"),
    ("contractAddress", "text"), ("cumulativeGasUsed", "int"), ("gasUsed", "int"), ("confirmations", "int"),
    ("methodId", "text"), ("functionName", "text"),
]
TX_COLUMNS = ["Account", "Time", "Amount"] + [name for name, _ in TX_FIELDS]


def option_text(name):
    value = omniscope_api.get_option(name)
    return "" if value is None else str(value).strip()


class EtherscanError(Exception):
    pass


class Etherscan:
    def __init__(self, api_key, chain_id):
        self.api_key = api_key
        self.chain_id = chain_id
        self.session = requests.Session()
        self.calls = 0

    def call(self, params):
        """One API call; returns the result list. Retries a few times when the rate limit is hit."""
        query = {"chainid": self.chain_id, **params, "apikey": self.api_key}
        for attempt in range(4):
            if self.calls:
                time.sleep(PAUSE)
            self.calls += 1
            try:
                r = self.session.request("GET", API_URL, params=query, timeout=TIMEOUT)
            except requests.RequestException as e:
                raise EtherscanError(f"Could not reach Etherscan: {type(e).__name__}")
            if r.status_code != 200:
                raise EtherscanError(f"Etherscan answered HTTP {r.status_code}.")
            try:
                body = r.json()
            except ValueError:
                raise EtherscanError("Etherscan's answer was not JSON.")
            result = body.get("result")
            if str(body.get("status")) == "1":
                return result if isinstance(result, list) else []
            text = result if isinstance(result, str) else ""
            message = str(body.get("message") or "")
            if message.startswith("No transactions found") or text.startswith("No transactions found"):
                return []
            if "rate limit" in text.lower() and attempt < 3:
                time.sleep(1.5)
                continue
            raise EtherscanError(f"Etherscan refused the request: {text or message or 'no reason given'}")
        raise EtherscanError("Etherscan's rate limit was still reached after several attempts.")


def to_coin(wei):
    try:
        return int(wei) / WEI
    except (TypeError, ValueError):
        return None


def balances(es, addresses):
    rows = []
    for i in range(0, len(addresses), BALANCE_BATCH):
        chunk = addresses[i:i + BALANCE_BATCH]
        omniscope_api.update_message(f"Balances {i + 1} to {i + len(chunk)} of {len(addresses)}")
        found = {}
        for item in es.call({"module": "account", "action": "balancemulti", "address": ",".join(chunk),
                             "tag": "latest"}):
            found[str(item.get("account", "")).lower()] = item.get("balance")
        for a in chunk:
            wei = found.get(a.lower())
            rows.append({"Account": a, "Balance": to_coin(wei), "Balance (wei)": None if wei is None else str(wei)})
    out = pd.DataFrame(rows, columns=BALANCE_COLUMNS)
    out["Balance"] = out["Balance"].astype("float64")
    return out


def transactions(es, address):
    """Every normal transaction of one address, oldest first. When a call returns the 10,000 maximum, the next
    call starts at the last block seen, and transactions already read are dropped."""
    seen, rows, start = set(), [], 0
    while True:
        page = es.call({"module": "account", "action": "txlist", "address": address, "startblock": start,
                        "page": 1, "offset": TX_PAGE, "sort": "asc"})
        for tx in page:
            if tx.get("hash") in seen:
                continue
            seen.add(tx.get("hash"))
            rows.append(tx)
        if len(page) < TX_PAGE:
            return rows
        last = int(page[-1].get("blockNumber", start))
        if last <= start:  # 10,000 transactions in one block: cannot page further
            return rows
        start = last
        omniscope_api.update_message(f"{address}: {len(rows)} transactions so far")


def typed_transactions(records):
    df = pd.DataFrame(records, columns=TX_COLUMNS)
    for name, kind in TX_FIELDS:
        if kind == "int":
            df[name] = pd.to_numeric(df[name], errors="coerce").astype("Int64")
        else:
            df[name] = df[name].astype(object)
    df["Time"] = pd.to_datetime(df["timeStamp"].astype("float64"), unit="s", utc=True)
    df["Amount"] = df["value"].map(to_coin).astype("float64")
    df["Account"] = df["Account"].astype(object)
    return df


api_key = option_text("apikey")
chain_id = option_text("chainid") or "1"
method = option_text("method") or "get_eth_balances"
address_field = omniscope_api.get_option("address")

if not api_key:
    omniscope_api.abort("Enter your Etherscan API key (create one at https://etherscan.io/myapikey).")
if not re.fullmatch(r"\d+", chain_id):
    omniscope_api.abort(f"Chain ID must be a number, such as 1 for Ethereum; got '{chain_id}'.")

input_data = omniscope_api.read_input_records(input_number=0)
if input_data is None:
    omniscope_api.abort("Connect a block with a field of addresses to the input.")
if not address_field or address_field not in input_data.columns:
    omniscope_api.abort("Choose the field that holds the addresses in 'Address field'.")

# Distinct addresses, in input order; values that are not addresses are reported and skipped
addresses, invalid = [], []
for value in input_data[address_field].tolist():
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NA:
        continue
    text = str(value).strip()
    if not text:
        continue
    if not ADDRESS.match(text):
        invalid.append(text)
    elif text.lower() not in {a.lower() for a in addresses}:
        addresses.append(text)

es = Etherscan(api_key, chain_id)
skipped = f" Skipped {len(invalid)} value(s) that are not addresses, such as '{invalid[0]}'." if invalid else ""

try:
    if method == "get_eth_balances":
        output = balances(es, addresses) if addresses else pd.DataFrame(
            {"Account": pd.Series(dtype=object), "Balance": pd.Series(dtype="float64"),
             "Balance (wei)": pd.Series(dtype=object)})
        omniscope_api.write_output_records(output, output_number=0)
        omniscope_api.close(f"Balances of {len(output)} address(es) on chain {chain_id}.{skipped}")
    elif method == "get_transactions_by_address":
        records = []
        for n, a in enumerate(addresses, 1):
            omniscope_api.update_message(f"Transactions of address {n} of {len(addresses)}")
            for tx in transactions(es, a):
                records.append({"Account": a, **{k: tx.get(k) for k, _ in TX_FIELDS}})
        output = typed_transactions(records)
        omniscope_api.write_output_records(output, output_number=0)
        omniscope_api.close(f"{len(output)} transactions of {len(addresses)} address(es) on chain {chain_id}."
                            f"{skipped}")
    else:
        omniscope_api.abort(f"Unknown method '{method}'.")
except EtherscanError as e:
    omniscope_api.abort(str(e))
