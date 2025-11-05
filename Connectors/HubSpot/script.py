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
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    def batch_associations(self, from_object_type, to_object_type, ids, batch_size=1000):
        """
        Retrieve associations between two object types for given IDs using v3 Associations API.
        Uses batching to respect the 1000 IDs per request limit.
        """
        endpoint = f"/crm/v3/associations/{from_object_type}/{to_object_type}/batch/read"
        all_results = []

        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            payload = {"inputs": [{"id": str(obj_id)} for obj_id in batch_ids]}
            response = self._make_request(endpoint, method="POST", payload=payload)
            all_results.extend(response.get("results", []))

        return self._flatten_associations(all_results, from_object_type, to_object_type)

    def _flatten_associations(self, associations, from_object_type, to_object_type):
        """
        Flatten the association results into multiple rows.
        Each `to` object will have its own row.
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
        Retrieve all object IDs for a given object type using v3 objects API.
        Example object_type: 'contacts', 'companies', 'deals', 'leads'.
        """
        endpoint = f"/crm/v3/objects/{object_type}"
        ids = []
        after = None

        while True:
            params = {"limit": 100}
            if after:
                params["after"] = after

            response = self._make_request(endpoint, params=params, method="GET")
            ids.extend([obj["id"] for obj in response.get("results", [])])

            paging = response.get("paging", {})
            next_page = paging.get("next")
            if next_page and "after" in next_page:
                after = next_page["after"]
            else:
                break

        return ids

    def list_leads(self):
        endpoint = '/crm/v3/objects/leads'
        leads = []
        after = None

        while True:
            params = {'limit': 100}
            if after:
                params['after'] = after

            response = self._make_request(endpoint, params)
            leads.extend(response['results'])

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
            params = {'limit': 100}
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
            params = {'limit': 100}
            # optional: explicitly ask for some properties
            params['properties'] = 'email,firstname,lastname,lifecyclestage'
            if after:
                params['after'] = after

            response = self._make_request(endpoint, params)
            contacts.extend(response['results'])

            if 'paging' in response and 'next' in response['paging']:
                after = response['paging']['next']['after']
            else:
                break

        return contacts

    def list_lists(self, processing_types=None, additional_properties=None, count=500):
        """
        Retrieve all lists (segments) using the v3 Lists Search API:
        POST /crm/v3/lists/search

        We page through all results using `hasMore` + `offset`.
        """
        endpoint = '/crm/v3/lists/search'
        lists = []
        offset = 0

        if processing_types is None:
            # No filter on processing type -> return all types
            processing_types = []
        if additional_properties is None:
            # No extra list properties beyond the defaults
            additional_properties = []

        while True:
            payload = {
                "offset": offset,
                "count": count,
                "additionalProperties": additional_properties,
            }
            if processing_types:
                payload["processingTypes"] = processing_types
            # If we omit "query" entirely, API returns all lists

            response = self._make_request(endpoint, method="POST", payload=payload)
            lists.extend(response.get('lists', []))

            if not response.get('hasMore'):
                break

            offset = response.get('offset', 0)

        return lists

    def list_deals(self):
        endpoint = '/crm/v3/objects/deals'
        deals = []
        after = None

        while True:
            params = {'limit': 100}
            if after:
                params['after'] = after

            response = self._make_request(endpoint, params)
            deals.extend(response['results'])

            if 'paging' in response and 'next' in response['paging']:
                after = response['paging']['next']['after']
            else:
                break

        return deals

    def search_contact(self, query, limit=100, properties=None):
        """
        Search contacts using v3 Search API:
        POST /crm/v3/objects/contacts/search
        """
        endpoint = '/crm/v3/objects/contacts/search'
        if properties is None:
            properties = ["email", "firstname", "lastname", "phone", "lifecyclestage"]

        all_results = []
        after = None

        while True:
            payload = {
                "query": query,
                "limit": limit,
                "properties": properties,
                # empty filterGroups -> rely on `query` full-text search
                "filterGroups": []
            }
            if after:
                payload["after"] = after

            response = self._make_request(endpoint, method="POST", payload=payload)
            all_results.extend(response.get("results", []))

            paging = response.get("paging", {})
            next_page = paging.get("next")
            if next_page and "after" in next_page:
                after = next_page["after"]
            else:
                break

        # Return in a consistent structure for the caller
        return {"results": all_results}

    def search_company(self, query, limit=100, properties=None):
        """
        Search companies using v3 Search API:
        POST /crm/v3/objects/companies/search
        """
        endpoint = '/crm/v3/objects/companies/search'
        if properties is None:
            properties = ["name", "domain", "website", "phone"]

        all_results = []
        after = None

        while True:
            payload = {
                "query": query,
                "limit": limit,
                "properties": properties,
                "filterGroups": []
            }
            if after:
                payload["after"] = after

            response = self._make_request(endpoint, method="POST", payload=payload)
            all_results.extend(response.get("results", []))

            paging = response.get("paging", {})
            next_page = paging.get("next")
            if next_page and "after" in next_page:
                after = next_page["after"]
            else:
                break

        return {"results": all_results}


omniscope_api = OmniscopeApi()

hubspot_api_key = omniscope_api.get_option("key")
hubspot_connector = HubspotConnector(hubspot_api_key)

action = omniscope_api.get_option("object")
query = omniscope_api.get_option("params")

from_object_type = omniscope_api.get_option("from_object_type")
to_object_type = omniscope_api.get_option("to_object_type")

# Parse the object_ids if provided as a comma-separated string
object_ids_input = omniscope_api.get_option("object_ids")
if object_ids_input:
    object_ids = [obj_id.strip() for obj_id in object_ids_input.split(",")]
else:
    object_ids = None

if action == "batch_associations":
    if not from_object_type or not to_object_type:
        omniscope_api.abort(
            "For the Associations action, both 'From Object' and 'To Object' options must be specified. "
            "Example values: 'Companies', 'Contacts'."
        )

    if not object_ids:
        # If no specific IDs provided, fetch all IDs for the `from_object_type`
        # Note: here `from_object_type` must match the v3 objects slug (e.g. 'contacts', 'companies')
        object_ids = hubspot_connector.list_object_ids(from_object_type)

    data = hubspot_connector.batch_associations(from_object_type, to_object_type, object_ids)

elif action == "list_companies":
    data = hubspot_connector.list_companies()

elif action == "list_leads":
    data = hubspot_connector.list_leads()

elif action == "list_contacts":
    data = hubspot_connector.list_contacts()

elif action == "list_lists":
    # Now returns a plain list of lists from v3
    data = hubspot_connector.list_lists()

elif action == "list_deals":
    data = hubspot_connector.list_deals()

elif action == "search_company":
    response = hubspot_connector.search_company(query)
    data = response["results"]

elif action == "search_contact":
    response = hubspot_connector.search_contact(query)
    data = response["results"]

else:
    omniscope_api.abort(f"Unknown action: {action}")

df = json_normalize(data)

if df is not None and not df.empty:
    omniscope_api.write_output_records(df, 0)
    omniscope_api.commit()
else:
    omniscope_api.close("No data retrieved")