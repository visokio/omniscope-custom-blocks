from omniscope.api import OmniscopeApi
import numpy as np
import pandas as pd
omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

if input_data is None:
    omniscope_api.abort("No input data")

separator = omniscope_api.get_option("separator")
# special cases
if separator == '\\n':
    separator = '\n'
elif separator == '\\t':
    separator = '\t'
elif separator == '\\r':
    separator = '\r'

if not separator:
    omniscope_api.abort("Enter the separator to split the text by")

selectedFields = omniscope_api.get_option("textFields")
if not selectedFields:
    omniscope_api.abort("Choose at least one text field to unstack")

# Pick the selected text fields (text can arrive as object or, with pandas 3, as the str dtype)
text_columns = [x for x in input_data.columns
                if x in selectedFields and pd.api.types.is_string_dtype(input_data[x].dtype)]

# Split each selected value into a list; values that are not text (missing values) stay as a one-item list
split_values = {
    col: [v.split(separator) if isinstance(v, str) else [v] for v in input_data[col]]
    for col in text_columns
}

# Each record becomes as many records as its longest list (at least one, so no record is lost)
lengths = np.ones(len(input_data), dtype=np.int64)
for col in text_columns:
    lengths = np.maximum(lengths, np.fromiter((len(x) for x in split_values[col]), dtype=np.int64,
                                              count=len(input_data)))

# Repeat the other fields, keeping their types, and fill shorter lists with empty strings
output_data = input_data.iloc[np.repeat(np.arange(len(input_data)), lengths)].reset_index(drop=True)
for col in text_columns:
    values = []
    for parts, n in zip(split_values[col], lengths):
        values.extend(parts)
        if len(parts) < n:
            values.extend([''] * (n - len(parts)))
    output_data[col] = pd.Series(values, index=output_data.index, dtype=object)

#write the output records in the first output
omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()
