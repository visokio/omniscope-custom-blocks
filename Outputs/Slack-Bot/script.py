from omniscope.api import OmniscopeApi
import json, pandas as pd, requests

omniscope_api = OmniscopeApi()

#create new contact
postMessageUrl = 'https://slack.com/api/chat.postMessage'

messagesToSend = []
jsonPosts = []
responses = []

input_data = omniscope_api.read_input_records(input_number=0)
#fix NaNs with empty string
input_data.fillna('', inplace=True)

for index, row in input_data.iterrows():
    message = row[omniscope_api.get_option("field")]
    channel = omniscope_api.get_option("channel")
    authToken = omniscope_api.get_option("authToken")
    messagesToSend.append({"Message" : message})

    if message:
        jsonPost = {
            "channel" : channel,
            "text" : message
        }
    
        jsonPosts.append(jsonPost)
    
        payload = jsonPost
        headers = {'content-type': 'application/json', 'Authorization': 'Bearer '+authToken}
        
        response = requests.post(postMessageUrl, data=json.dumps(payload), headers=headers)
        if response:
            #success
            responses.append({"Response" : response.json()})
        else: 
            #blow up
            raise Exception('Some error occurred while posting the message '+message+' on channel '+channel+'. Request returned: '+ str(response.status_code) + ' ' + response.text)

    
output_data = pd.DataFrame(messagesToSend)
output_data_2 = pd.DataFrame(responses)

#print(output_data)
#print(output_data_2)

if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
if output_data_2 is not None:
    omniscope_api.write_output_records(output_data_2, output_number=1)

omniscope_api.close()