from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()
import pandas as pd
import requests
import time

class DuneAnalyticsAPI:
    BASE_URL = 'https://api.dune.com/api/v1'

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = {
            'x-dune-api-key': self.api_key,
            'Content-Type': 'application/json'
        }

    def execute_query(self, query_id):
        base_url = f'{self.BASE_URL}/query/{query_id}/execute'
        params = {
              "performance": "large",
        }
        response = requests.post(base_url, headers=self.headers, params=params)
        omniscope_api.update_message(f'Submitted query {query_id}')
        return response.json()['execution_id']

    def poll_execution_status(self, execution_id):
        while True:
            url = f'{self.BASE_URL}/execution/{execution_id}/status'
            response = requests.get(url, headers=self.headers)
            status = response.json()['state']
            if status == 'QUERY_STATE_COMPLETED':
                omniscope_api.update_message(f'Execution completed... retrieving results...')
                return status
            omniscope_api.update_message(f'Execution status: {status}')
            time.sleep(5)  # Wait for 5 seconds before polling again

    def retrieve_execution_results(self, execution_id):
        url = f'{self.BASE_URL}/execution/{execution_id}/results'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def get_latest_query_results(self, query_id):
        url = f'{self.BASE_URL}/query/{query_id}/results'
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()

        return response.json()


api = DuneAnalyticsAPI(omniscope_api.get_option("duneApiKey"))
queryID = omniscope_api.get_option("queryId")
result = None

if (omniscope_api.get_option("mode") == "execAndRetrieve") :
    execution_id = api.execute_query(queryID)
    api.poll_execution_status(execution_id)
    results = api.retrieve_execution_results(execution_id)
else :
    results = api.get_latest_query_results(queryID)

output_data = pd.json_normalize(results)
output_data_2 = pd.json_normalize(results['result']['rows'])


if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
    
if output_data_2 is not None:
    omniscope_api.write_output_records(output_data_2, output_number=1)    

omniscope_api.close()