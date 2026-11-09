# Dune

Loads the result of a saved Dune query, public or your own: its latest stored result, or a fresh execution. Every page of rows is read, with numbers and dates typed from Dune's column types.

Dune (dune.com) is a service for SQL queries over indexed blockchain data; its users publish many queries, and anyone with an API key can read their results. This block reads one saved query's result through the Dune API:

- **Retrieve latest query results** (the default) reads the result Dune stored from the query's last run. It starts no execution; Dune refuses it if the query was never run, its SQL has changed since, or the stored result has expired.
- **Execute and retrieve latest results** runs the query now on the chosen **engine size**, reports progress (pending, executing, queue position) in the block's message while waiting, and then reads the new result. A run that fails, is cancelled or expires stops the block with Dune's own error message.
- Every page of the result is read (Dune limits the rows per request and says where the next page starts).
- Columns come out in the query's order and are typed from Dune's column types: whole numbers as Integer, `double` and `decimal` as Decimal, `boolean` as true/false, `date` and `timestamp` as dates in UTC. `uint256` and `int256` (too large for a number field), `varbinary` (hex), and arrays, maps and rows (as JSON) are text.

## Language and libraries

Python. It uses requests (Apache License 2.0) for the HTTP calls and pandas (BSD 3-Clause) for the output. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

None. The block is a source: it reads from Dune.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Dune API key | `duneApiKey` | Password | An API key from your Dune account's API settings. |
| Query ID | `queryId` | Text | The number after `/queries/` in the query's address (`241` for https://dune.com/queries/241/388), or the whole address. |
| Query mode | `mode` | Choice | **Retrieve latest query results** (`retrieveLatest`, the default) or **Execute and retrieve latest results** (`execAndRetrieve`). |
| Engine size | `performance` | Choice | For Execute only: **Small**, **Medium** (the default, Dune's default) or **Large** (`small` / `medium` / `large`). Larger engines suit heavy queries and can use more credits. |

## Outputs

- **Execution** (`Output Data`): one record about the run: Execution ID, Query ID, State (such as `QUERY_STATE_COMPLETED`), Submitted, Started, Ended, Expires (dates, UTC; Dune keeps results for 90 days), Rows (the result's total row count).
- **Results** (`Output Data 2`): the query's rows, typed as above.

A result Dune had to cut short (state `QUERY_STATE_COMPLETED_PARTIAL`) is still written, and the block's message says it is partial.

## Limits

- Reading results and executing queries use Dune credits from your plan; an execution also counts against the plan's limits on concurrent runs.
- Query parameters are not set by the block: Execute runs the query with its saved default parameters, and Retrieve reads the latest result whatever parameters it ran with.
- Waiting has no time limit of its own: the block waits as long as Dune reports the run as pending or executing (cancel the block in Omniscope to stop waiting; the execution continues on Dune).
- In tests, 100,000 rows in four pages took a few seconds; against Dune, time is mostly the query's run time and the download.

## Source

[script.py](script.py)

The tests in `tests/` run the script against an invented Dune result (`tests/canned/results.json`, written by `tests/make_canned.py`) for an invented query of daily trades by chain; `sample-data/placeholder.csv` is the Results output for it, for trying a workflow without an API key.
