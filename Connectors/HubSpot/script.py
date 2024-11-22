# author: Antonio-GPT
import os
import requests
import pandas as pd
from pandas import json_normalize
from omniscope.api import OmniscopeApi

class HubspotConnector:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://api.hubapi.com'

    def _make_request(self, endpoint, params=None, method="GET", payload=None):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        url = f"{self.base_url}{endpoint}"

        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=payload)

        response.raise_for_status()
        return response.json()



    def batch_associations(self, from_object_type, to_object_type, ids):
        """
        Retrieve associations between two object types for given IDs using v3 API.
        :param from_object_type: Object type to retrieve associations from (e.g., 'Companies').
        :param to_object_type: Object type to retrieve associations to (e.g., 'Deals').
        :param ids: List of object IDs to retrieve associations for.
        :return: List of flattened association results.
        """
        endpoint = f"/crm/v3/associations/{from_object_type}/{to_object_type}/batch/read"
        payload = {
            "inputs": [{"id": str(obj_id)} for obj_id in ids]
        }
        response = self._make_request(endpoint, method="POST", payload=payload)
        return self._flatten_associations(response.get("results", []), from_object_type, to_object_type)

    def _flatten_associations(self, associations, from_object_type, to_object_type):
        """
        Flatten the association results into multiple rows.
        Each `to` object will have its own row.
        :param associations: List of association results from the API.
        :param from_object_type: Object type to retrieve associations from (e.g., 'Companies').
        :param to_object_type: Object type to retrieve associations to (e.g., 'Deals').
        :return: Flattened list of dictionaries.
        """
        flattened_data = []
        for association in associations:
            from_id = association.get("from", {}).get("id")
            for to in association.get("to", []):
                flattened_data.append({
                    f"{from_object_type}_id": from_id,
                    f"{to_object_type}_id": to.get("id"),
                    "association_type": to.get("type"),
                })
        return flattened_data

    def list_object_ids(self, object_type):
        """
        Retrieve all object IDs for a given object type.
        :param object_type: Object type to retrieve IDs for (e.g., 'Companies').
        :return: List of object IDs.
        """
        endpoint = f"/crm/v3/objects/{object_type}"
        ids = []
        after = None

        while True:
            params = {"limit": 100}
            if after:
                params["after"] = after

            response = self._make_request(endpoint, method="GET")
            ids.extend([obj["id"] for obj in response["results"]])

            if "paging" in response and "next" in response["paging"]:
                after = response["paging"]["next"]["after"]
            else:
                break

        return ids
        
        
        
    def list_leads(self):
        endpoint = '/crm/v3/objects/leads'
        leads = []
        after = None

        while True:
            params = {'limit': 100}  # Maximum allowed limit is 100
            if after:
                params['after'] = after

            response = self._make_request(endpoint, params)
            leads.extend(response['results'])

            # Check for pagination
            if 'paging' in response and 'next' in response['paging']:
                after = response['paging']['next']['after']
            else:
                break

        return leads

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
            params['properties'] = 'email,lifecycleStage'
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
elif action == "list_leads":
    data = hubspot_connector.list_leads()
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