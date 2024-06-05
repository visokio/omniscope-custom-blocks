from omniscope.api import OmniscopeApi
import pandas as pd
import json
omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

jsonField = omniscope_api.get_option("jsonField")
includeInput = omniscope_api.get_option("includeInput")

output_data = None
dataframes_list = []  # List to store each dataframe

for index, row in input_data.iterrows():
    if not(isinstance(row[jsonField], str)):
        continue
    jsonString = str(row[jsonField])
    if not jsonString:
        continue

    dictJson = json.loads(jsonString)
    dataframe = pd.json_normalize(dictJson)
    dataframe = dataframe.add_prefix(jsonField+'_')
    
    if includeInput:
        new_cols = list(input_data.columns.values)
        dataframe[new_cols] = row.values.tolist()

    dataframes_list.append(dataframe)

# Concatenate all dataframes in the list
output_data = pd.concat(dataframes_list, ignore_index=True)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()
