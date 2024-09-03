from omniscope.api import OmniscopeApi
import pandas as pd

omniscope_api = OmniscopeApi()

fieldName = omniscope_api.get_option("fieldName")

# Initialize a global variable to keep track of the total rows processed
total_rows_processed = 0

def handle_chunk(chunk):
    global total_rows_processed
    global fieldName
    
    # Calculate the new index value by adding the total number of rows processed so far
    chunk[fieldName] = range(total_rows_processed + 1, total_rows_processed + len(chunk) + 1)
    
    # Update the total number of rows processed after handling this chunk
    total_rows_processed += len(chunk)
    
    return chunk

# Process the data stream by applying the function to each data chunk
omniscope_api.process_stream(handle_chunk)

# Close the data stream
omniscope_api.close()
