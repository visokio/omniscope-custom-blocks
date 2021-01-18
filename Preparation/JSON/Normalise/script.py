from omniscope.api import OmniscopeApi
import pandas as pd
import json
omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

jsonField = omniscope_api.get_option("jsonField")

output_data = None
for index, row in input_data.iterrows():
    if not(isinstance(row[jsonField], str)):
        continue
    jsonString = str(row[jsonField])
    if not jsonString:
        continue
    print(jsonString)
    dictJson = json.loads(jsonString)
    dataframe = pd.json_normalize(dictJson)
    if output_data is None:
        output_data = dataframe
    else:
        output_data = output_data.append(dataframe, ignore_index=True)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()