from omniscope.api import OmniscopeApi
import os, pandas as pd, json
from slack import WebClient

omniscope_api = OmniscopeApi()

client = WebClient(token=omniscope_api.get_option("authToken"))

methodType = omniscope_api.get_option("methodType");
if ("POST" == methodType):
   response = client.api_call(
     api_method=omniscope_api.get_option("methodName"),
     http_verb=omniscope_api.get_option("methodType"),
     json=json.loads(omniscope_api.get_option("jsonPayload"))
   )
else:
   response = client.api_call(
     api_method=omniscope_api.get_option("methodName"),
     http_verb=omniscope_api.get_option("methodType"),
     params=json.loads(omniscope_api.get_option("params")),
   ) 

output_data = pd.DataFrame(data=pd.json_normalize(response.data))
output_data_2 = pd.DataFrame(data=[response], columns={'Text Response'})


#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
if output_data_2 is not None:
    omniscope_api.write_output_records(output_data_2, output_number=1)
omniscope_api.close()