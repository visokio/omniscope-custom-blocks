import pandas as pd
from omniscope.api import OmniscopeApi

# Initialize Omniscope API
omniscope_api = OmniscopeApi()

# Function to sort dataframe columns based on given option
def sort_dataframe_columns(df, sort_by='name'):
    if sort_by == 'name':
        sorted_columns = sorted(df.columns)
    elif sort_by == 'type':
        sorted_columns = sorted(df.dtypes.items(), key=lambda x: str(x[1]))
        sorted_columns = [col[0] for col in sorted_columns]
    else:
        raise ValueError("sort_by must be either 'name' or 'type'")
    
    return df[sorted_columns]

# Fetch the sorting option ('name' or 'type') from the block options
sort_by_option = omniscope_api.get_option('sortBy')

# Process the data stream using the lambda function
omniscope_api.process_stream(lambda data: sort_dataframe_columns(data, sort_by=sort_by_option))

# Close the API after processing is complete
omniscope_api.close()