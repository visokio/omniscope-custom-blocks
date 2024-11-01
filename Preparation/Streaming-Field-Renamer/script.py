import pandas as pd
from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

# Load rename rules from a CSV file
rules_file_path = omniscope_api.get_option("rules")
rename_rules = pd.read_csv(rules_file_path)

# Ensure the CSV contains the necessary columns
if "Current Name" not in rename_rules.columns or "New Name" not in rename_rules.columns:
    omniscope_api.abort("The rename rules file must contain columns 'Current Name' and 'New Name'.")

# Create a dictionary mapping current names to new names
rename_map = dict(zip(rename_rules["Current Name"], rename_rules["New Name"]))

def handle_chunk(chunk):
    # Rename columns based on the rename_map
    chunk = chunk.rename(columns=rename_map)
    
    # Return the modified chunk
    return chunk

# Process each incoming chunk with the renaming function
omniscope_api.process_stream(handle_chunk)