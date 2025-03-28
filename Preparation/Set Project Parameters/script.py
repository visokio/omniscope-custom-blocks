from omniscope.api import OmniscopeApi
import urllib3
import json

def send_update(omniscope_api, message):
    try:
        omniscope_api.update_message(message)
    except Exception:
        pass  # For compatibility with older API versions

# Initialize the Omniscope API
omniscope_api = OmniscopeApi()

# Read input records from the first input block.
input_data = omniscope_api.read_input_records(input_number=0)

# Read the column names from the block options that contain the parameter names and values.
params_name_option = omniscope_api.get_option("Params_Name")
params_value_option = omniscope_api.get_option("Params_Value")

# Build the list of parameter updates from the input data.
updates_list = []
for index, row in input_data.iterrows():
    param_name = row[params_name_option]
    param_value = row[params_value_option]
    updates_list.append({
        "name": param_name,
        "value": param_value
    })

# Build the JSON payload for the update request.
payload = json.dumps({
    "updates": updates_list,
    "waitForIdle": False
})

# Retrieve the Iox_File_Url from the block options.
iox_url = omniscope_api.get_option("Iox_File_Url")
if not iox_url.endswith("/"):
    iox_url += "/"

# Construct the URL for updating project parameters.
update_params_url = iox_url + "w/updateparams"

# Create an HTTP pool manager.
http = urllib3.PoolManager()

# Log that the project parameter update is being enqueued.
send_update(omniscope_api, "Updating project parameters from input data...")

# Send a single POST request with all parameter updates.
http.request('POST', update_params_url, headers={'Content-Type': 'application/json'}, body=payload)

# Close the Omniscope API with a completion message.
omniscope_api.close("Project parameters update enqueued.")