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

# Read the parameter name and value from Omniscope options.
# Ensure that your block has options "Param_Name" and "Param_Value" defined.
param_name = omniscope_api.get_option("Param_Name")
param_value = omniscope_api.get_option("Param_Value")

# Build the JSON payload for the parameter update request.
payload = json.dumps({
    "updates": [
        {
            "name": param_name,
            "value": param_value
        }
    ],
    "waitForIdle" : False
})

# Retrieve the Iox_File_Url from the block options.
iox_url = omniscope_api.get_option("Iox_File_Url")
if not iox_url.endswith("/"):
    iox_url += "/"

# Construct the URL for updating project parameters.
update_params_url = iox_url + "w/updateparams"

# Create an HTTP pool manager.
http = urllib3.PoolManager()

# Log the update attempt.
send_update(omniscope_api, f"Updating parameter '{param_name}' with value '{param_value}'...")

# Send the POST request to update the parameter.
http.request('POST', update_params_url, headers={'Content-Type': 'application/json'}, body=payload)

# Close the API with a completion message.
omniscope_api.close(f"Parameter '{param_name}' update enqueued.")