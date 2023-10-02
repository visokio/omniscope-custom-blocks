from omniscope.api import OmniscopeApi

import urllib3
import json
import time

#Tries to send updates to Omniscope.
def send_update(omniscope_api, message):
    try:
        omniscope_api.update_message(message)
    except AttributeError:
        pass # old api version, ignore the message

def check_response(omniscope_api, response):
        if response.status == 200:
            return # all good
        else:
            omniscope_api.abort("Unexpected server error "+str(response))

def update_parameters(omniscope_api, http, iox_url, param_names, param_values):
    update_params_url = iox_url + "w/updateparams"  
    update_param_value_json = json.dumps({"updates" : [{"name" : name, "value" : value} for (name, value) in zip(param_names, param_values)]})
    response = http.request('POST', update_params_url, headers={'Content-Type': 'application/json'}, body=update_param_value_json )
    check_response(omniscope_api, response)
    update_param_response = json.loads(response.data)
    if (update_param_response["status"] != "SUCCESS"):
        omniscope_api.abort("Error updating project parameters" + str(update_param_response.data))


def start_wf_execution(omniscope_api, http, iox_url, block_names, refresh_from_source):
    start_wf_execution_url = iox_url + "w/execute"
    execute_workflow_json = json.dumps({"blocks" : block_names, "refreshFromSource" : refresh_from_source, "cancelExisting" : False})
    job_id = None
    while(job_id == None):
        response = http.request('POST', start_wf_execution_url, headers={'Content-Type': 'application/json'}, body=execute_workflow_json)
        start_wf_execution_response = json.loads(response.data)
        err = start_wf_execution_response.get("errorType")
        if (err != None):
            if (err == "WORKFLOW_ALREADY_RUNNING"):
                time.sleep(1)
                continue
            else:
                omniscope_api.abort(err)
        job_id = start_wf_execution_response["jobId"]
    return job_id

def wait_job_termination(omniscope_api, http, iox_url, job_id):
    check_job_url =  iox_url + "w/job/" + job_id + "/state"
    job_state = None
    while(True):
        time.sleep(1)
        response = http.request('GET', check_job_url)
        check_response(omniscope_api, response)
        job_state = json.loads(response.data)["jobState"]
        if (job_state not in ["RUNNING", "BLOCKED", "QUEUED"]):
            break
    return job_state

omniscope_api = OmniscopeApi()

#options parsing
iox_url = omniscope_api.get_option("Iox_File_Url")
if not iox_url.endswith("/"):
    iox_url = iox_url + "/"

refresh_from_source = str(omniscope_api.get_option("Refresh_From_Source")).lower()
block_names = []
block_names_option = omniscope_api.get_option("Block_Names")
if (block_names_option is not None):
    for block_name in block_names_option.split(','):
        block_names.append(block_name.strip())

param_names = omniscope_api.get_option("Parameters")

#reading param values from the input
block_input = omniscope_api.read_input_records(input_number=0)
param_values_list = []
for index, row in block_input.iterrows():
    param_values_list.append([row[param_name] for param_name in param_names])

http = urllib3.PoolManager()


ignore_errors = omniscope_api.get_option("ignore_errors")

#For each set of param, update the project parameters and execute the workflow.
for param_values in param_values_list:
    update_parameters(omniscope_api, http, iox_url, param_names, param_values)
    send_update(omniscope_api, "Running workflow with " + str([(n,v) for (n,v) in zip(param_names, param_values)]))
    job_state = None
    while (job_state != "COMPLETED"):
        job_id = start_wf_execution(omniscope_api, http, iox_url, block_names, refresh_from_source)
        job_state = wait_job_termination(omniscope_api, http, iox_url, job_id)
        if job_state == "FAILED":
            if ignore_errors:
                break
            else:
                omniscope_api.abort("Worfklow execution failed: "+job_state)

omniscope_api.close()