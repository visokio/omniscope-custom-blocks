# Google BigQuery Export

Loads the input records into a Google BigQuery table, appending them or replacing the table's contents; the table is created if it doesn't exist.

Publish what a workflow produces (cleaned data, forecasts, scores) to BigQuery, where other teams and tools can query it.

- Give the **table ID** as `project.dataset.table`. The dataset must exist; the table is created on the first run.
- **Append records** (the default) adds the records to the table, whose columns must match. Unticked, every run **replaces** the table's records and columns.
- Field names become **BigQuery column names**: characters other than letters, digits and underscores become underscores (`Sale date` → `Sale_date`, `Revenue (£)` → `Revenue____`), a name starting with a digit gets a leading underscore, names starting with one of BigQuery's reserved prefixes (`_TABLE_`, `_FILE_`, `_PARTITION`, `_ROW_TIMESTAMP`, `__ROOT__`, `_COLIDENTIFIER`) get a leading `f`, and names that then clash (BigQuery ignores case) get `_2`, `_3`. The block's message lists every renamed field.
- Field types decide the column types: text to STRING, whole numbers to INT64, decimal numbers to FLOAT64, dates to TIMESTAMP, true/false to BOOL.
- Sign in with a **service account's JSON key file** on the Omniscope server, or leave it empty to use the server's own Google credentials. A key file applies to this block only.

## Inputs
- **Input 1**: the records to load. Any fields.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| JSON key file | `ApplicationCredentials` | File path | Optional. The path, on the Omniscope server, of a service account's JSON key file. Empty: the server's own Google credentials. |
| Table ID | `TableId` | Text | `project.dataset.table`, for example `my-project.sales.orders`. Created if it does not exist; the dataset must exist. |
| Append records | `AppendData` | Yes/no | Ticked: the records are added to the table. Unticked: the table's records and columns are replaced on every run. Default: ticked. |

The service account needs **BigQuery Job User** on the project and **BigQuery Data Editor** on the dataset.

## Outputs
None. The block's message reports what was loaded, for example "Appended 20 records in my-project.retail.store_daily_totals".

## Errors
Problems stop the block with BigQuery's first line, for example "BigQuery: 400 Provided Schema does not match Table ..." when appended records don't fit the table's columns. An unconnected input, an empty table ID, no credentials or a missing key file stop it with a message before anything is sent.

## Size of input
The records are sent to BigQuery as one load job. In tests, preparing 300,000 records took well under a second; sending them depends on the network.

<!--language-->
## Language and libraries

Python. It uses pandas, google-cloud-bigquery, pyarrow and db-dtypes.

pandas is part of Omniscope's Python environment. google-cloud-bigquery, pyarrow and db-dtypes (all Apache License 2.0) are listed in the manifest's dependencies; Omniscope installs them on first run if they are missing.
<!--/language-->

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented.
