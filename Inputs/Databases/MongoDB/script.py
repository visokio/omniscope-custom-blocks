"""MongoDB: reads the documents of a MongoDB collection, all of them or those matching a query."""
import datetime
import json
import math

import pandas as pd
import pymongo as mongo
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

TIMEOUT_MS = 20000  # give up on an unreachable server after 20 seconds, not the driver's 30


def text_option(name):
    value = omniscope_api.get_option(name)
    return value.strip() if isinstance(value, str) else ""


connection_url = text_option("connection_url")
host = text_option("host")
port = omniscope_api.get_option("port")
user = text_option("user")
password = omniscope_api.get_option("password") or ""
auth_source = text_option("auth_source")
database = text_option("database")
collection = text_option("collection")
full_data = omniscope_api.get_option("full_data")
query = text_option("query")
limit = omniscope_api.get_option("limit")

if not database or not collection:
    omniscope_api.abort("Enter the database and the collection to read.")
if not connection_url and not host:
    omniscope_api.abort("Enter a connection URL, or the host and port.")
if limit is not None and limit < 0:
    omniscope_api.abort("Limit must be 0 (no limit) or more.")
if user and not password:
    omniscope_api.abort("Enter the password for the user, or clear the user name.")

query_json = None
if not full_data and query:
    try:
        query_json = json.loads(query)
    except ValueError as exc:
        omniscope_api.abort(f"The custom query is not valid JSON ({exc}). Field names and text need double quotes, "
                            'for example {"age": {"$gte": 20}}.')
    if not isinstance(query_json, dict):
        omniscope_api.abort('The custom query must be a JSON object, for example {"age": {"$gte": 20}}.')

if connection_url:
    client = mongo.MongoClient(connection_url, serverSelectionTimeoutMS=TIMEOUT_MS)
else:
    kwargs = {"host": host, "port": int(port or 27017), "serverSelectionTimeoutMS": TIMEOUT_MS}
    if user:
        # Let the server and driver agree the mechanism (SCRAM-SHA-256 or, on older servers, SCRAM-SHA-1)
        kwargs.update(username=user, password=password, authSource=auth_source or "admin")
    client = mongo.MongoClient(**kwargs)


def missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def plain(value):
    """BSON values Omniscope has no field type for: ObjectId, Decimal128, UUID, binary, regex and the like."""
    if isinstance(value, (str, int, float, bool, datetime.datetime)):
        return value
    if hasattr(value, "to_decimal"):  # Decimal128
        return float(value.to_decimal())
    return str(value)


def json_default(value):
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    return str(value)


def cell(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=json_default)
    return value if missing(value) else plain(value)


try:
    cursor = client[database][collection].find(query_json)
    if limit:
        cursor = cursor.limit(int(limit))
    documents = list(cursor)
except Exception as exc:  # unreachable server, failed sign-in, bad operator in the query...
    omniscope_api.abort(f"MongoDB: {type(exc).__name__}: {str(exc).split(', Timeout:')[0][:500]}")
finally:
    client.close()

if not documents:
    omniscope_api.close("No documents matched" if query_json else "The collection is empty")
else:
    data = pd.DataFrame(documents)
    for col in data.columns:
        s = data[col].map(cell)
        present = s[~s.map(missing)]
        kinds = set(present.map(lambda v: "number" if isinstance(v, (int, float)) and not isinstance(v, bool)
                                else type(v).__name__))
        if len(kinds) > 1:
            # A field holding numbers in some documents and text in others becomes text
            s = s.map(lambda v: v if missing(v) else (v.isoformat() if isinstance(v, datetime.datetime) else str(v)))
        data[col] = s
    omniscope_api.write_output_records(data, output_number=0)
    omniscope_api.close(f"{len(data)} documents")
