# Flipside

Runs a SQL query on Flipside's blockchain data tables through the Flipside API and writes every page of the result. Flipside has wound down its public query tools, so the API may no longer accept queries.

## Service status

Flipside Crypto offered free SQL access to decoded blockchain data (Ethereum, Solana and many other chains) through its Studio and an API with a Python software development kit (SDK), which this block uses. Since then:

- Flipside closed its Studio on 1 July 2025 (announced on its X account on 23 June 2025, offering its data through a cloud data-sharing platform instead).
- SonarX announced on 19 May 2026 that it had acquired Flipside's blockchain data business.
- Flipside's SDK repository on GitHub (FlipsideCrypto/sdk) was archived on 2 July 2026 and is read-only.

No notice found says whether the API itself still accepts queries. If the block reports that Flipside cannot be reached, or the API refuses your key, the service has most likely ended; the community **Dune** block is an alternative for SQL over blockchain data.

## What the block does

- Sends the SQL query with your API key, asking for a fresh result (no cached result is reused) and waiting up to 20 minutes for it.
- Reads every page of the result (10,000 rows a page) and writes them as one output; Flipside's internal row number (`__row_index`) is dropped.
- A query with no rows gives an empty output with the query's columns.
- Flipside's errors (SQL errors, rate limit, timeout, server or API errors) stop the block with Flipside's message.

Values are written as Flipside returns them: numbers as numbers, dates and timestamps as ISO text (convert them with a Field Organiser or Formula if needed).

## Language and libraries

Python. It uses the `flipside` Python SDK (MIT licence, archived July 2026) and pandas (BSD 3-Clause). Omniscope installs `flipside` on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

None. The block is a source: it runs a query on Flipside.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| API key | `key` | Password | Your Flipside API key. |
| SQL query | `query` | Text | The SQL to run on Flipside's data tables (such as `ethereum.core.fact_transactions`). |

## Outputs

- **Query results** (`Output Data`): every row of the query's result, with its columns in the query's order.

## Limits

- Depends on a service that may have ended (see Service status).
- Queries run for at most 20 minutes; a longer one stops with a timeout message.

## Source

[script.py](script.py)

The tests in `tests/` run the script against an invented query result (`tests/canned/query-result.json`, written by `tests/make_canned.py`) with a stand-in for the Flipside SDK. `sample-data/placeholder.csv` is the block's output for that result.
