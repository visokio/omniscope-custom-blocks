# Salesforce REST OAuth

Loads Salesforce data through OAuth 2.0 and the REST API, with a simple object picker that automatically loads all available fields.

Authentication uses the OAuth 2.0 **Client Credentials** flow, which suits a workflow that runs unattended: no user signs in when it runs.

- **Simple - Load object** (the default): choose a common object (Accounts, Contacts, Opportunities, Cases and ten more). The block asks Salesforce which fields the Run As user can read, and loads all of them, without you writing SOQL or knowing field API names.
- **Query Builder**: an object, a list of fields (relationship fields such as `Owner.Name` included), a WHERE and an ORDER BY.
- **Custom SOQL**: any SOQL query.
- Every page of results is followed. **Date and date-time fields come out as dates** (UTC); lookups through relationships come out as dotted field names (`Owner.Name`).
- Optionally **deleted and archived** records too, and a **maximum** number of records.
- Two schema actions list the objects available and describe an object's fields, for finding API names.
- Rate limits and temporary Salesforce errors are retried; other errors stop the block with Salesforce's message. Secrets never appear in messages.

## Salesforce setup

1. In Salesforce Setup, create or configure an **External Client App** with OAuth enabled and the **Manage user data via APIs (`api`)** scope.
2. Enable the **Client Credentials Flow** and choose its **Run As** user in the app policies. That user's Salesforce permissions decide which objects and fields this block can read; a dedicated integration user with read access to what you need is best.
3. Copy the app's **Consumer Key** and **Consumer Secret** into the OAuth options.
4. Enter your Salesforce **My Domain URL**, such as `https://your-company.my.salesforce.com`.

REST API access must be enabled for the Salesforce org and edition.

## Language and libraries

Python. It uses requests (Apache License 2.0) for the HTTP calls and pandas (BSD 3-Clause) for the output. Omniscope installs requests on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

None. The block is a source: it reads from Salesforce.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Salesforce My Domain URL | `authBaseUrl` | Text | HTTPS My Domain URL used for OAuth, such as `https://acme.my.salesforce.com`. |
| Client ID / Consumer Key | `clientId` | Text | Consumer Key of the External Client App. |
| Client Secret / Consumer Secret | `clientSecret` | Password | Consumer Secret of the External Client App. |
| Action | `operation` | Choice | Load data (default); Advanced - List available objects; Advanced - Describe fields for object. |
| Load mode | `queryMode` | Choice | Simple - Load object (default); Advanced - Query Builder; Advanced - Custom SOQL. |
| Salesforce object | `simpleObject` | Choice | For Simple mode: Accounts (default), Contacts, Leads, Opportunities, Cases, Campaigns, Tasks, Events, Users, Products, Price Books, Orders, Contracts, Assets. |
| Include deleted/archived records | `includeDeleted` | Choice | No (default) or Yes: also deleted (Recycle Bin) and archived records, through the queryAll resource. |
| Maximum records | `maxRecords` | Text | Stop after this many records (default 100000); the final message says when the limit was reached. 0 loads every record. |
| Object API name (advanced) | `objectName` | Text | For Query Builder and Describe fields, such as `Account` or `MyObject__c`. |
| Fields (advanced) | `fields` | Text | For Query Builder: comma-separated field API names (default `Id, Name`). |
| WHERE clause (advanced) | `whereClause` | Text | For Query Builder, without the word WHERE, such as `CreatedDate = LAST_N_DAYS:30`. |
| ORDER BY clause (advanced) | `orderBy` | Text | For Query Builder, without the words ORDER BY, such as `CreatedDate DESC`. |
| Custom SOQL (advanced) | `soql` | Text | For Custom SOQL mode, such as `SELECT Id, Name, Owner.Name FROM Account`. |
| REST API version | `apiVersion` | Text | `auto` (default) uses the newest version the org offers, or give one such as `62.0`. |
| HTTP timeout (seconds) | `timeoutSeconds` | Text | Timeout for each request (default 60). |

## Outputs

- **Records** (`Output Data`):
  - Load data: one record per Salesforce record. In Simple mode the fields are the object's readable fields in Salesforce's order (compound address and location fields are left out; their parts, such as BillingCity, are included). Date and date-time fields are dates in UTC; a lookup through a relationship is a dotted field name (`Owner.Name`); other lists are JSON text.
  - List available objects: one record per object (name, label, key prefix, whether it can be queried, created, updated, deleted, and whether it is custom).
  - Describe fields: one record per field of the object (name, label, type, length, precision, flags, relationship and what it refers to).

When a query in Simple or Query Builder mode finds nothing, the output has the queried fields and no records. A Custom SOQL query that finds nothing gives no output.

## Limits

- Uses the synchronous REST Query API, one request per page of up to 2,000 records, so a large object takes many requests; the default Maximum records stops at 100,000. For millions of records Salesforce recommends its Bulk API, which this block does not use.
- In Simple mode the query names every field; an object with several hundred custom fields gives a long query, and Salesforce limits the length of a query sent in the address. Query Builder with the fields you need avoids it.
- Text in Custom SOQL or Query Builder results that is entirely in Salesforce's date format (`2025-03-04` or `2025-03-04T09:15:00.000+0000`) is read as a date.
- In tests, 40,000 records over 20 canned pages took under a second; against Salesforce, the time is Salesforce's response time per page.

## Source

[script.py](script.py)

The tests in `tests/` run the script against invented Salesforce responses (`tests/canned/`, written by `tests/make_canned.py`); `sample-data/placeholder.csv` is the Records output for the invented accounts, for trying a workflow without a Salesforce org.
