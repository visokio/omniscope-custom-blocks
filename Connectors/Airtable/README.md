# Airtable

Reads every record of an Airtable table, or of one of its views, through the Airtable REST API, one record per row.

Airtable returns at most 100 records per request, with a marker for the next page. The block follows the pages until the last one, so the whole table arrives in one output, with the record ID first and one field per Airtable field.

- Choose the table by **name or ID**; names with spaces, slashes or other symbols work as typed.
- Optionally read only a **view** (its filters and sort order apply) or the records that match a **filter formula**, such as `{Status} = 'Open'`.
- **Lists and objects** (attachments, linked records, collaborators, multiple selects) arrive as JSON text, for example `["weekend", "group"]`. The community JSON Normalise and JSON Expand fields blocks turn them into fields.
- Airtable **leaves empty values out** of a record, so they arrive empty. A checkbox field (whose values are all true or missing) arrives as true/false, with false for an unticked box.
- A field holding text in some records and numbers in others (a formula that sometimes returns an error, for example) arrives as text.
- The record ID field is called `id`. If the table has its own field called `id`, that field keeps the name and the record ID is called `Airtable record ID`.
- If Airtable answers "too many requests" (it allows 5 requests a second per base), the block waits 30 seconds and tries again, up to 4 times.

## Inputs
None. The block reads from Airtable.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Personal access token | `token` | Password | An Airtable personal access token with the `data.records:read` scope and access to the base. |
| Base ID | `base_id` | Text | The ID of the base: the part of the table's web address that starts with `app`. |
| Table name or ID | `table` | Text | The table's name, exactly as shown in Airtable, or its ID (starts with `tbl`). |
| View | `view` | Text | Optional. A view's name or ID (starts with `viw`): only the records in that view are read, in its order. |
| Filter formula | `filter_formula` | Text | Optional. An Airtable formula; only records for which it is true are read, for example `{Status} = 'Open'`. |
| Page size | `page_size` | Whole number | Records per request, from 1 to 100 (Airtable's maximum). All pages are read whatever the size. Default: 100. |

To find the IDs, open the table in a web browser: the address has the form `https://airtable.com/appXXXXXXXX/tblXXXXXXXX/viwXXXXXXXX`.

## Outputs
- **Records** (`Output Data`): one record per Airtable record: `id`, then the table's fields in the order they first appear. An empty table (or view, or filter) gives an output with only the `id` field and no records.

## Errors
A wrong token, base, table, view or formula stops the block with Airtable's message and a hint, for example "Airtable returned 403: INVALID_PERMISSIONS_OR_MODEL_NOT_FOUND: ... Check that the token has the data.records:read scope and access to this base."

## Size of input
Each page is one request, so a table of 10,000 records takes 100 requests. In tests against canned responses, 6,000 records in 60 pages were read and converted in under a second; the time on a real server is mostly Airtable's response time.

<!--language-->
## Language and libraries

Python. It uses pandas and requests.

pandas is part of Omniscope's Python environment. requests (Apache License 2.0) is listed in the manifest's dependencies; Omniscope installs it on first run if it is missing.
<!--/language-->

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented: `placeholder.csv` is what the block outputs for the invented table in `tests/`.
