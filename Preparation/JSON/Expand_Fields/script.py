from omniscope.api import OmniscopeApi
import pandas as pd
import json

# Initialize Omniscope API
omniscope_api = OmniscopeApi()

# Read the records associated with the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# Get options
jsonField = omniscope_api.get_option("jsonField")
includeInput = omniscope_api.get_option("includeInput")

# Function to parse JSON and add prefix to keys
def parse_json(row, jsonField):
    try:
        json_dict = json.loads(row[jsonField])
        return {f"{jsonField}_{k}": v for k, v in json_dict.items()}
    except (json.JSONDecodeError, TypeError):
        return {}

# Apply the JSON parsing function to each row
json_expanded = input_data.apply(parse_json, axis=1, jsonField=jsonField)

# Convert the list of dictionaries into a DataFrame
expanded_df = pd.DataFrame(json_expanded.tolist())

# Concatenate the original input data and the expanded JSON data
if includeInput:
    output_data = pd.concat([input_data, expanded_df], axis=1)
else:
    output_data = expanded_df

# Write the output records in the first output
if not output_data.empty:
    omniscope_api.write_output_records(output_data, output_number=0)

# Close the Omniscope API
omniscope_api.close()