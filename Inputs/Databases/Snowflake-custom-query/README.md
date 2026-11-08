# Snowflake Custom Query

Runs a SQL query on Snowflake, signing in with a password or a key pair, and outputs the result.

A short Python script around Snowflake's own connector: give the account, the user, a way to sign in and a query, and the result arrives as one record per row.

- Sign in with a **password**, or with a **key pair**: the path of the user's private key file (PEM, PKCS#8) on the Omniscope server and, for an encrypted key, its password. Snowflake accounts that block password sign-in need the key pair. The key file is used when both are given.
- **Warehouse, database, schema and role** are optional; empty ones use the user's defaults.
- The whole result is read into memory. For large tables the core **Database** block (Snowflake connection) is the better choice.
- Types: whole NUMBERs arrive as whole numbers, NUMBERs with decimals (which the connector returns as Python decimals) as decimal numbers, DATE as dates, TIMESTAMP_NTZ as dates with times, TIMESTAMP_TZ and TIMESTAMP_LTZ in UTC, TIME as text such as `09:30:00`, BINARY as hexadecimal text.
- Snowflake returns unquoted column names in capitals. Two columns with the same name (`SELECT a.ID, b.ID`) become `ID` and `ID_2`.
- A statement that returns no result set ends with "The statement ran but returned no table" and no output records.

## Inputs
None. The block reads from Snowflake.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Account identifier | `account` | Text | The part of your Snowflake address before `.snowflakecomputing.com`, for example `myorg-myaccount` (or a locator such as `xy12345.eu-west-1`). |
| User | `user` | Text | The Snowflake user to sign in as. |
| Password | `password` | Password | The user's password. Leave empty when signing in with a private key file. |
| Private key file | `private_key_file` | File path | For key-pair sign-in: the path, on the Omniscope server, of the user's private key (PEM, PKCS#8). Used instead of the password. |
| Private key password | `private_key_password` | Password | The passphrase of an encrypted private key. Empty for an unencrypted key. |
| Warehouse | `warehouse` | Text | Optional. The warehouse that runs the query. Empty: the user's default. |
| Database | `database` | Text | Optional. The database for table names that don't name one. Empty: the user's default. |
| Schema | `schema` | Text | Optional. The schema for table names that don't name one. |
| Role | `role` | Text | Optional. The role to use. Empty: the user's default role. |
| SQL query | `custom_sql` | Text | The query to run. |

## Outputs
- **Results** (`Output Data`): one record per row the query returns, with the query's columns as fields. A query that returns no rows gives its fields and no records.

## Errors
A failed sign-in stops the block with "Could not connect to Snowflake: ..." and Snowflake's message; a failed query with "Error running the query: ..." and Snowflake's message, for example "SQL compilation error". Missing settings stop it before connecting.

## Size of input
The whole result is held in memory. In tests against a canned 200,000-row result, building and converting the table took well under a second; the query itself runs in Snowflake and is billed as warehouse time.

<!--language-->
## Language and libraries

Python. It uses pandas and snowflake-connector-python.

pandas is part of Omniscope's Python environment. snowflake-connector-python (Apache License 2.0) is listed in the manifest's dependencies; Omniscope installs it on first run if it is missing.
<!--/language-->

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented: `placeholder.csv` is the block's output for the invented query result in `tests/`.
