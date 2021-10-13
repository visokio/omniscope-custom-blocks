#!/usr/bin/env python

import os

from omniscope.api import OmniscopeApi
from google.cloud import bigquery

def execute_query(query):
    bqclient = bigquery.Client()
    query_job = bqclient.query(query)
    return query_job.result().to_dataframe()

def main():
    omniscope_api = OmniscopeApi()
    try:
        key_file = omniscope_api.get_option("ApplicationCredentials")
        if key_file is not None:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = key_file
        query = omniscope_api.get_option("Query")
        data_frame = execute_query(query)
        omniscope_api.write_output(data_frame, 0)    
        omniscope_api.close()
    except Exception as e:
        omniscope_api.cancel(str(e))
        raise e

if __name__ == "__main__":
    main()