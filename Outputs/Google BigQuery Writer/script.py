#!/usr/bin/env python

import os
import re

from omniscope.api import OmniscopeApi
from google.cloud import bigquery

def sanitise_field_name(field_name):
    """
    Fields must contain only letters, numbers, and underscores, start with a letter or underscore, and be at most 300 characters long.
    """
    sanitised = re.sub("[^0-9a-zA-Z]", "_", field_name)
    if not re.match("^[a-zA-Z_]+.*", sanitised):
        sanitised = "_"+sanitised
    return sanitised[:300]

def sanitise(data_frame):
    """
    :return: a :class: pandas.core.frame.DataFrame with field renamed as to be valid column names for big query tables
    """
    columns_mapper = {field_name:sanitise_field_name(field_name) for field_name in data_frame.columns.values.tolist()}
    if len(columns_mapper.keys()) != len(set(columns_mapper.values())):
        # there are duplicates in the column names. Very unlikely to happen in practice.
        raise Exception("Unable to detemine a map for dataframe, you should rename your columns manually")
    return data_frame.rename(columns = columns_mapper)

def write_to_big_query_table(data_frame, table_id, append_data=True):
    client = bigquery.Client()
    write_disposition=bigquery.WriteDisposition.WRITE_APPEND if append_data else bigquery.WriteDisposition.WRITE_TRUNCATE
    job_config = bigquery.LoadJobConfig(
        write_disposition=write_disposition
    ) # append records by defualt, schema will be retrieved from data_frame
    job = client.load_table_from_dataframe(sanitise(data_frame), destination=table_id, job_config=job_config)
    job.result()


def main():
    omniscope_api = OmniscopeApi()
    key_file = omniscope_api.get_option("ApplicationCredentials")
    if key_file is not None:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = key_file
    table_id = omniscope_api.get_option("TableId")
    append_data = omniscope_api.get_option("AppendData")
    data_frame = omniscope_api.read_input_records(input_number=0)
     
    write_to_big_query_table(data_frame=data_frame, table_id=table_id, append_data=append_data)    
    omniscope_api.close()

if __name__ == "__main__":
    main()
