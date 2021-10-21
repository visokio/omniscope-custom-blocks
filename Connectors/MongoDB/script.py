from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

import pandas as pd
import pymongo as mongo
import json
import urllib.parse

host = omniscope_api.get_option("host")
port = omniscope_api.get_option("port")
database = omniscope_api.get_option("database")
collection = omniscope_api.get_option("collection")
query = omniscope_api.get_option("query")
limit = omniscope_api.get_option("limit")
user = omniscope_api.get_option("user")
password = omniscope_api.get_option("password")
auth_source = omniscope_api.get_option("auth_source")
full_data = omniscope_api.get_option("full_data")


if user and password and auth_source:
	client = mongo.MongoClient(f"mongodb://{host}:{port}/", username=user, password=password, authMechanism='SCRAM-SHA-256', authSource=auth_source) 
else:
	client = mongo.MongoClient(f"mongodb://{host}:{port}/") 
db = client[database]
col = db[collection]

query_json = None if not query or full_data else json.loads(query)

cursor = col.find(query_json)

if limit:
	cursor.limit(limit)

output_data = pd.DataFrame(list(cursor))

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()