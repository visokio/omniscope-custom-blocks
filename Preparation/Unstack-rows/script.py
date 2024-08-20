from omniscope.api import OmniscopeApi
import pandas as pd
omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

separator = omniscope_api.get_option("separator")
# special cases
if separator == '\\n':
    separator = '\n'
elif separator == '\\t':
    separator = '\t'
elif separator == '\\r':
    separator = '\r'
    

# Find text columns in the DataFrame
text_columns = input_data.select_dtypes(include='object').columns
selectedFields = omniscope_api.get_option("textFields")
# Pick selected text fields
text_columns = [x for x in text_columns if x in selectedFields]

# Initialize an empty DataFrame to store the result
result_df = pd.DataFrame()

# Initialize a list to store the resulting DataFrames
result_frames = []

# Iterate through each row
for index, row in input_data.iterrows():
    # Split newline-separated strings into lists for each text column
    split_row = row.copy()
    max_length = 0
    
    for col in text_columns:
        if isinstance(split_row[col], str):  # Check if the value is a string
            split_row[col] = split_row[col].split(separator)
            max_length = max(max_length, len(split_row[col]))  # Find the max length of lists
        else:
            split_row[col] = [split_row[col]]  # Keep non-string values as they are, but inside a list
            
    # If max_length is zero, skip this row
    if max_length == 0:
        continue
    
    # Fill shorter lists with empty strings to match the longest list's length
    for col in text_columns:
        current_length = len(split_row[col])
        if current_length < max_length:
            split_row[col].extend([''] * (max_length - current_length))
    
    # Explode the row
    exploded_row = pd.DataFrame({col: split_row[col] for col in input_data.columns})
    exploded_row.index = [index] * max_length
    result_frames.append(exploded_row)

# Concatenate the list of DataFrames to get the final result
result_df = pd.concat(result_frames)
output_data = result_df

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()