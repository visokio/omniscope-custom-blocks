from omniscope.api import OmniscopeApi
import urllib3
import json

def send_update(omniscope_api, message):
    try:
        omniscope_api.update_message(message)
    except Exception:
        pass  # Ignore for older API versions

def read_block_names(option_value):
    return [name.strip() for name in option_value.split(',')] if option_value else []

# Initialize the Omniscope API
omniscope_api = OmniscopeApi()

# Check the Execute flag; exit early if false.
if omniscope_api.get_option("execute") != True:
    omniscope_api.close("Execution flag is false. Skipping workflow execution.")
    exit()

# Parse options
iox_url = omniscope_api.get_option("Iox_File_Url")
if not iox_url.endswith("/"):
    iox_url += "/"

block_names = read_block_names(omniscope_api.get_option("Block_Names"))
refresh_from_source = omniscope_api.get_option("Refresh_From_Source")

# Prepare the payload for the workflow execution request
payload = json.dumps({
    "blocks": block_names,
    "refreshFromSource": refresh_from_source,
    "cancelExisting": True,
    "waitForIdle": False
})

# Build the execution URL
execution_url = iox_url + "w/execute"

http = urllib3.PoolManager()

# Send the POST request and immediately return
send_update(omniscope_api, "Enqueuing workflow execution...")
http.request('POST', execution_url, headers={'Content-Type': 'application/json'}, body=payload)

omniscope_api.close("Workflow execution enqueued.")