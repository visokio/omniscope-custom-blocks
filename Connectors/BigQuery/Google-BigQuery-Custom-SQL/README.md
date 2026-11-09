# Google BigQuery Custom SQL

Runs a SQL query (GoogleSQL) on Google BigQuery and outputs the result, with BigQuery's types mapped to Omniscope field types.

Let BigQuery do the heavy lifting (joins and aggregations over large tables) and bring only the result into the workflow.

- Type the query in **GoogleSQL**, naming tables in full: `` `project.dataset.table` ``.
- Sign in with a **service account's JSON key file** on the Omniscope server, or leave it empty to use the server's own Google credentials (the `GOOGLE_APPLICATION_CREDENTIALS` environment variable, or the service account of a Google Cloud machine). A key file applies to this block only.
- Optionally set the **project** the query runs in and is billed to; by default the key file's project.
- Types follow the result's schema, so every run gives the same field types: INT64 to whole numbers, FLOAT64 and NUMERIC/BIGNUMERIC to decimal numbers, BOOL to true/false, DATE to dates, DATETIME and TIMESTAMP to dates with times (TIMESTAMP in UTC), TIME to text such as `09:00:00`, arrays, STRUCT and JSON to JSON text, BYTES to base64 text, GEOGRAPHY to WKT text.
- A statement that returns no table (INSERT, UPDATE, CREATE TABLE...) runs and ends with "The statement ran but returned no table (N rows affected)", with no output records. Such statements change data with the service account's permissions, so if the block should only read, give the service account read-only roles (those below).

## Inputs
None. The block reads from BigQuery.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| JSON key file | `ApplicationCredentials` | File path | Optional. The path, on the Omniscope server, of a service account's JSON key file. Empty: the server's own Google credentials. |
| Project | `ProjectId` | Text | Optional. The Google Cloud project the query runs in and is billed to. Default: the key file's project, or the server's default project. |
| SQL query | `Query` | Text | A GoogleSQL query. Name tables in full: `project.dataset.table`. |

The service account needs the **BigQuery Job User** role on the project that runs the query and **BigQuery Data Viewer** on the data it reads.

## Outputs
- **Results** (`Output Data`): one record per row the query returns, with the query's columns as fields. A query that returns no rows gives its fields and no records.

## Errors
Problems stop the block with BigQuery's own first line, for example "BigQuery: 400 Syntax error: Unexpected identifier at [1:1]". No credentials, or a key file that isn't there, stop it with "Could not sign in to Google Cloud: ..." or "The JSON key file ... was not found on the server."

## Size of input
The whole result is held in memory. In tests against a canned 200,000-row result, converting the types took well under a second; the time on a real server is mostly BigQuery's. Queries are billed by BigQuery by the data they scan.

<!--language-->
## Language and libraries

Python. It uses pandas, google-cloud-bigquery, pyarrow and db-dtypes.

pandas is part of Omniscope's Python environment. google-cloud-bigquery, pyarrow and db-dtypes (all Apache License 2.0) are listed in the manifest's dependencies; Omniscope installs them on first run if they are missing.
<!--/language-->

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented: `placeholder.csv` is the block's output for the invented query result in `tests/`.
