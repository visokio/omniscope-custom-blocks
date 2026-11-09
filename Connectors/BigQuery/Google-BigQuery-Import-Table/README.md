# Google BigQuery Import Table

Reads a whole Google BigQuery table or view, page by page, with BigQuery's types mapped to Omniscope field types.

Bring a BigQuery table into a workflow as it is: reference data, a curated table, or the output of a scheduled query.

- Give the **table ID** as `project.dataset.table` (the older `project:dataset.table` form works too).
- **Tables** are read directly with BigQuery's row-listing API, page by page, which BigQuery does not bill as a query. **Views, materialised views and external tables** can't be listed that way, so they are read with `SELECT *`, which is billed as a query.
- Sign in with a **service account's JSON key file** on the Omniscope server, or leave it empty to use the server's own Google credentials. A key file applies to this block only.
- Optionally read only the first **maximum records**, to try out a large table.
- Types follow the table's schema, so every page gets the same field types: INT64 to whole numbers, FLOAT64 and NUMERIC/BIGNUMERIC to decimal numbers, BOOL to true/false, DATE to dates, DATETIME and TIMESTAMP to dates with times (TIMESTAMP in UTC), TIME to text, arrays, STRUCT and JSON to JSON text, BYTES to base64 text, GEOGRAPHY to WKT text.

## Inputs
None. The block reads from BigQuery.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| JSON key file | `ApplicationCredentials` | File path | Optional. The path, on the Omniscope server, of a service account's JSON key file. Empty: the server's own Google credentials. |
| Table ID | `TableId` | Text | The table's ID: `project.dataset.table`, for example `my-project.sales.orders`. A view works too. |
| Page size | `PageSize` | Whole number | Records per request (default 10,000). All pages are read whatever the size. |
| Maximum records | `MaxRows` | Whole number | Optional. Read only the first this many records. Empty or 0 reads them all. |

The service account needs **BigQuery Data Viewer** on the table, and for a view also **BigQuery Job User** on the project.

## Outputs
- **Table** (`Output Data`): the table's records, with its columns as fields, written page by page. An empty table gives its fields and no records.

## Errors
Problems stop the block with BigQuery's first line, for example "BigQuery: 404 Not found: Table my-project:sales.missing was not found in location EU". No credentials, or a key file that isn't there, stop it with "Could not sign in to Google Cloud: ..." or "The JSON key file ... was not found on the server."

## Size of input
Each page is held in memory while it is converted and written. In tests against a canned 250,000-row table read in pages of 25,000, the conversion took well under a second; the time on a real server is mostly BigQuery's and the network's.

<!--language-->
## Language and libraries

Python. It uses pandas, google-cloud-bigquery, pyarrow and db-dtypes.

pandas is part of Omniscope's Python environment. google-cloud-bigquery, pyarrow and db-dtypes (all Apache License 2.0) are listed in the manifest's dependencies; Omniscope installs them on first run if they are missing.
<!--/language-->

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented: `placeholder.csv` is the block's output for the invented table in `tests/`.
