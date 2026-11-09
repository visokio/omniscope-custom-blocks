# MongoDB

Reads the documents of a MongoDB collection, all of them or those matching a JSON query, one record per document.

Bring application data kept in MongoDB (orders, users, events, enrolments) into a workflow, where it can be joined, aggregated and reported.

- Connect with a **connection URL** (`mongodb://...` or `mongodb+srv://...` for Atlas), or with **host and port** and, if needed, a **user**, **password** and **authentication database** (`admin` when empty). The driver and server agree the sign-in mechanism (SCRAM-SHA-256, or SCRAM-SHA-1 on older servers).
- Read the **whole collection**, or untick it and give a **custom query** in JSON, for example `{"age": {"$gte": 20}}` or `{"address.town": "Leeds"}`. A **limit** caps the number of documents.
- Each **top-level key** becomes a field. **Nested objects and arrays** arrive as JSON text: the community **JSON Normalise** and **JSON Expand fields** blocks turn them into fields.
- Values Omniscope has no type for become text (`_id` ObjectIds, UUIDs, regular expressions); Decimal128 becomes a decimal number; dates stay dates (MongoDB stores them in UTC).
- A key holding numbers in some documents and text in others becomes text, so no value is lost.
- An unreachable server stops the block after 20 seconds.

## Inputs
None. The block reads from MongoDB.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Connection URL | `connection_url` | Password | Optional. A MongoDB connection string, for example `mongodb+srv://user:password@cluster0.example.net/`. When given, the connection and authentication settings below are not used. |
| Host | `host` | Text | The server's name or IP address. Default: 127.0.0.1. |
| Port | `port` | Whole number | The port MongoDB listens on; usually 27017. Default: 27017. |
| User | `user` | Text | Optional. The user to sign in as; empty for a server without authentication. |
| Password | `password` | Password | The user's password. |
| Authentication database | `auth_source` | Text | Optional. The database the user was created in. Empty: admin. |
| Database | `database` | Text | The database that holds the collection. |
| Collection | `collection` | Text | The collection to read. |
| Whole collection | `full_data` | Yes/no | Ticked: every document is read and the custom query is ignored. Unticked: only the documents matching the custom query. Default: ticked. |
| Custom query | `query` | Text | A MongoDB filter in JSON, used when "Whole collection" is unticked. Names and text need double quotes. |
| Limit | `limit` | Whole number | Optional. The most documents to read. Empty or 0: no limit. |

## Outputs
- **Documents** (`Output Data`): one record per document, one field per top-level key (in the order they first appear), objects and arrays as JSON text. When nothing matches, the block writes no records and says "No documents matched" (or "The collection is empty"): with no documents there are no keys to make fields from.

## Errors
A query that isn't valid JSON stops the block with a message showing the right form. Connection and sign-in problems stop it with the driver's message, for example "MongoDB: ServerSelectionTimeoutError: db.example.com:27017: timed out".

## Size of input
All matching documents are held in memory. In tests, 100,000 documents with an array and an object each were converted in under a second once read; reading them depends on the server and network.

<!--language-->
## Language and libraries

Python. It uses pandas and pymongo.

pandas is part of Omniscope's Python environment. pymongo (Apache License 2.0) is listed in the manifest's dependencies; Omniscope installs it on first run if it is missing.
<!--/language-->

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented: `placeholder.csv` is the block's output for the invented documents in `tests/`.
