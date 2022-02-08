#!/usr/bin/env python

import os

from omniscope.api import OmniscopeApi
from google.cloud import bigquery

def read_big_query_table(table_id, page_size):
    bqclient = bigquery.Client()
    table = bigquery.TableReference.from_string(table_id=table_id)
    return bqclient.list_rows(table, page_size = page_size).to_dataframe_iterable()


def main():
    omniscope_api = OmniscopeApi()
    try:
        key_file = omniscope_api.get_option("ApplicationCredentials")
        if key_file is not None:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = key_file
        page_size = omniscope_api.get_option("PageSize")
        if page_size is None:
            page_size = 10_000
        table_id = omniscope_api.get_option("TableId")
        for data_frame in read_big_query_table(table_id=table_id, page_size = page_size):
            omniscope_api.write_output(data_frame, 0)
        omniscope_api.close()
    except Exception as e:
        omniscope_api.cancel(str(e))
        raise e

if __name__ == "__main__":
    main()