#!/usr/bin/env python

import os

from omniscope.api import OmniscopeApi
from google.cloud import bigquery

def read_big_query_table(table_id):
    bqclient = bigquery.Client()
    table = bigquery.TableReference.from_string(table_id=table_id)
    return bqclient.list_rows(table).to_dataframe()


def main():
    omniscope_api = OmniscopeApi()
    try:
        key_file = omniscope_api.get_option("ApplicationCredentials")
        if key_file is not None:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = key_file
        table_id = omniscope_api.get_option("TableId")
        data_frame = read_big_query_table(table_id=table_id)
        omniscope_api.write_output(data_frame, 0)    
        omniscope_api.close()
    except Exception as e:
        omniscope_api.cancel(str(e))
        raise e

if __name__ == "__main__":
    main()