# Etherscan

Loads the native-coin balances, or the full transaction lists, of the Ethereum addresses in a field, from the Etherscan API (Ethereum and other chains by chain ID).

Etherscan indexes public blockchains and answers questions about any address. This block takes a field of addresses from the workflow and asks Etherscan's API (version 2) about each one:

- **Balances**: one record per address, with its current balance in the chain's coin (ether on Ethereum) and the exact value in wei (1 ether = 10^18 wei) as text. Addresses are sent 20 to a call.
- **Transactions**: one record per normal transaction each address sent or received, oldest first, with the time as a date, the amount in the chain's coin, and the fields Etherscan returns (block, hash, from, to, gas, error flag and so on). Etherscan returns at most 10,000 transactions a call; for busier addresses the block asks again from the last block it has seen, until it has them all.

Repeated addresses are looked up once. Values that are not addresses (`0x` followed by 40 hexadecimal characters), such as names ending in `.eth`, are skipped and counted in the block's message. The calls are paced to stay within the free plan's 3 calls a second, and a call refused for the rate limit is retried.

## Language and libraries

Python. It uses requests (Apache License 2.0) for the HTTP calls and pandas (BSD 3-Clause) for the output. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

- **Input 1**: records with a text field of addresses. Other fields are not used (join the output back on Account to keep them).

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| API key | `apikey` | Password | Your Etherscan API key, from https://etherscan.io/myapikey. One key works for every chain Etherscan serves; the free plan covers selected chains. |
| What to load | `method` | Choice | **Balances** (`get_eth_balances`, the default) or **Transactions** (`get_transactions_by_address`). |
| Chain ID | `chainid` | Text | The chain to query: 1 for Ethereum (the default), 8453 for Base, 42161 for Arbitrum One, and so on. |
| Address field | `address` | Field | The field that holds the addresses. From input 1. |

## Outputs

- **Results** (`Output Data`):
  - Balances: **Account** (the address as given), **Balance** (decimal, in the chain's coin), **Balance (wei)** (text: whole wei amounts are larger than an Integer field can hold).
  - Transactions: **Account** (the address it was loaded for), **Time** (date, UTC), **Amount** (decimal, in the chain's coin), then Etherscan's fields: blockNumber, timeStamp, hash, nonce, blockHash, transactionIndex, from, to, value (wei, text), gas, gasPrice, isError, txreceipt_status, input, contractAddress, cumulativeGasUsed, gasUsed, confirmations, methodId, functionName. Numbers are Integer fields; addresses and hashes are text.

A transaction between two addresses of the input appears once for each of them.

## Limits

- Normal transactions only: internal transactions and token transfers (ERC-20, NFTs) are separate Etherscan calls that the block does not make.
- The free plan allows 3 calls a second and 100,000 calls a day, and covers selected chains only; a chain outside the plan is refused with Etherscan's message. Balances take one call per 20 addresses; transactions at least one call per address.
- Amounts in the chain's coin are decimals (about 15 significant digits); use the wei text fields where every digit matters.
- Etherscan's terms of use apply to the data.

## Source

[script.py](script.py)

The tests in `tests/` run the script against invented Etherscan responses (`tests/canned/`, written by `tests/make_canned.py`, which also writes `sample-data/addresses.csv`); the addresses in them are random. `sample-data/placeholder.csv` is the Transactions output for those responses, for trying a workflow without an API key.
