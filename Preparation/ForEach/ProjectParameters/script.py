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


omniscope_api = OmniscopeApi()


param_names = omniscope_api.get_option("Parameters")

#reading param values from the input
block_input = omniscope_api.read_input_records(input_number=0)
param_values_list = []
projects_list = []
iox_url_option = omniscope_api.get_option("Iox_File_Url")
for index, row in block_input.iterrows():
    param_values_list.append([row[param_name] for param_name in param_names])
    url = row[iox_url_option]
    if not url.endswith("/"):
        url = url + "/"
    projects_list.append(url)
    
http = urllib3.PoolManager()

#For each set of param, update the project parameters
for i in range(len(param_values_list)):
    iox_url = projects_list[i]
    param_values = param_values_list[i]
    send_update(omniscope_api, "Updating workflow "+iox_url+" with " + str([(n,v) for (n,v) in zip(param_names, param_values)]))
    update_parameters(omniscope_api, http, iox_url, param_names, param_values)


#write the input data in the first output
if block_input is not None:
    omniscope_api.write_output_records(block_input, output_number=0)
omniscope_api.close()