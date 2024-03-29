# author: Antonio-GPT
import os
import requests
import pandas as pd
from pandas.io.json import json_normalize
from omniscope.api import OmniscopeApi

class HubspotConnector:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://api.hubapi.com'

    def _make_request(self, endpoint, params=None):
        headers = {
        "Authorization": f"Bearer {self.api_key}"
        }
        url = f'{self.base_url}{endpoint}'
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def list_companies(self):
        endpoint = '/crm/v3/objects/companies'
        companies = []
        after = None

        while True:
            params = {'limit': 100}  # maximum allowed limit is 100
            if after:
                params['after'] = after

            response = self._make_request(endpoint, params)
            companies.extend(response['results'])

            if 'paging' in response and 'next' in response['paging']:
                after = response['paging']['next']['after']
            else:
                break
  
        return companies

    def list_contacts(self):
        endpoint = '/crm/v3/objects/contacts'
        contacts = []
        after = None

        while True:
            params = {'limit': 100}  # maximum allowed limit is 100
            if after:
                params['after'] = after

            response = self._make_request(endpoint, params)
            contacts.extend(response['results'])

            if 'paging' in response and 'next' in response['paging']:
                after = response['paging']['next']['after']
            else:
                break
  
        return contacts

    def list_lists(self):
        endpoint = '/contacts/v1/lists'
        lists = []
        offset = 0
        has_more = True

        while has_more:
            params = {'count': 250, 'offset': offset}  # Maximum count is 250
            response = self._make_request(endpoint, params)
            lists.extend(response['lists'])

            has_more = response['has-more']
            offset = response['offset']

        return lists

  
    def list_deals(self):
        endpoint = '/crm/v3/objects/deals'
        deals = []
        after = None

        while True:
            params = {'limit': 100}  # Maximum limit is 100
            if after:
                params['after'] = after

            response = self._make_request(endpoint, params)
            deals.extend(response['results'])

            if 'paging' in response and 'next' in response['paging']:
                after = response['paging']['next']['after']
            else:
                break

        return deals

    def search_contact(self, query):
        endpoint = f'/contacts/v1/search/query?q={query}'
        return self._make_request(endpoint)

omniscope_api = OmniscopeApi()

hubspot_api_key = omniscope_api.get_option("key")
hubspot_connector = HubspotConnector(hubspot_api_key)

action = omniscope_api.get_option("object")
query = omniscope_api.get_option("params")

if action == "list_companies":
    data = hubspot_connector.list_companies()
elif action == "list_contacts":
    data = hubspot_connector.list_contacts()
elif action == "list_lists":
    response = hubspot_connector.list_lists()
    data = response["lists"]
elif action == "list_deals":
    data = hubspot_connector.list_deals()
elif action == "search_company":
    response = hubspot_connector.search_company(query)
    data = response["results"]
elif action == "search_contact":
    response = hubspot_connector.search_contact(query)
    data = response["contacts"]

df = json_normalize(data)

omniscope_api.write_output_records(df, 0)
omniscope_api.commit()