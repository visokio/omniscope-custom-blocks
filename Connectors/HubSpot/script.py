"""HubSpot connector: loads companies, contacts, leads, deals, lists, forms, form submissions and associations
from HubSpot's CRM APIs with a private app access token, following every page."""
import json
import re
import time

import requests
import pandas as pd
from pandas import json_normalize
from omniscope.api import OmniscopeApi

TIMEOUT = 60
MAX_RETRIES = 5
OBJECT_TYPES = {"companies", "contacts", "deals", "leads", "tickets", "products", "line_items", "quotes",
                "calls", "emails", "meetings", "notes", "tasks"}
ISO_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


class HubSpotError(Exception):
    pass


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

        for attempt in range(MAX_RETRIES + 1):
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            # HubSpot limits private apps to a number of calls per 10 seconds: wait and try again
            if response.status_code == 429 and attempt < MAX_RETRIES:
                time.sleep(min(float(response.headers.get("Retry-After") or 10), 60))
                continue
            break

        if not response.ok:
            try:
                message = response.json().get("message") or response.text
            except ValueError:
                message = response.text
            if response.status_code == 401:
                raise HubSpotError("HubSpot refused the access token (401). Check the private app access token.")
            if response.status_code == 403:
                raise HubSpotError(f"HubSpot refused access (403): {message[:300]} The private app needs the "
                                   "read scope for this object.")
            raise HubSpotError(f"HubSpot returned {response.status_code} for {endpoint}: {message[:300]}")
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

    def list_objects(self, object_type, properties=None):
        """All records of a CRM object (companies, contacts, deals, leads...), 100 per request.
        Without `properties`, HubSpot returns its default properties for the object."""
        endpoint = f'/crm/v3/objects/{object_type}'
        records = []
        after = None

        while True:
            params = {'limit': 100}
            if properties:
                params['properties'] = ','.join(properties)
            if after:
                params['after'] = after

            response = self._make_request(endpoint, params)
            records.extend(response['results'])

            if 'paging' in response and 'next' in response['paging']:
                after = response['paging']['next']['after']
            else:
                break

        return records

    def list_leads(self, properties=None):
        return self.list_objects('leads', properties)

    def list_companies(self, properties=None):
        return self.list_objects('companies', properties)

    def list_contacts(self, properties=None):
        # Without a choice, the contact's name, e-mail and lifecycle stage
        return self.list_objects('contacts', properties or ['email', 'firstname', 'lastname', 'lifecyclestage'])

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

    def list_deals(self, properties=None):
        return self.list_objects('deals', properties)

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

    # ----- Forms and form submissions -----

    def list_forms(self, include_all_types=True):
        """
        List forms using the Forms v2 API:
        GET /forms/v2/forms

        - By default, HubSpot only returns marketing forms.
        - To include non-marketing forms (pop-ups, non-HubSpot, etc.),
          you must pass formTypes=ALL.

        Returns a plain list of form objects.
        """
        endpoint = "/forms/v2/forms"
        params = {}

        if include_all_types:
            # Include ALL form types; marketing + non-marketing
            params["formTypes"] = "ALL"  # case sensitive

        response = self._make_request(endpoint, params=params, method="GET")

        # The endpoint returns a raw JSON array of forms
        if isinstance(response, list):
            return response

        # Fallback, in case HubSpot ever wraps it:
        return response.get("forms", [])

    def list_form_submissions(self, form_guid, page_size=50):
        """
        Get 'insights' for a specific form by retrieving ALL submissions and
        flattening field values into columns.

        Uses legacy endpoint:
        GET /form-integrations/v1/submissions/forms/{form_guid}

        Returns a list of dicts like:
        {
            "conversionId": ...,
            "submittedAt": ...,
            "pageUrl": ...,
            "<field_name_1>": "<value>",
            "<field_name_2>": "<value>",
            ...
        }
        """
        endpoint = f"/form-integrations/v1/submissions/forms/{form_guid}"
        all_submissions = []
        after = None

        while True:
            params = {"limit": page_size}
            if after:
                params["after"] = after

            response = self._make_request(endpoint, params=params, method="GET")

            submissions = response.get("results", [])
            all_submissions.extend(submissions)

            paging = response.get("paging", {})
            next_page = paging.get("next")
            if next_page and "after" in next_page:
                after = next_page["after"]
            else:
                break

        # Flatten field values into columns for Omniscope
        flattened = []
        for sub in all_submissions:
            row = {
                "conversionId": sub.get("conversionId"),
                "submittedAt": sub.get("submittedAt"),
                "pageUrl": sub.get("pageUrl"),
            }
            for field in sub.get("values", []):
                name = field.get("name")
                value = field.get("value")
                if name:
                    row[name] = value
            flattened.append(row)

        return flattened


def option_text(name):
    value = omniscope_api.get_option(name)
    return "" if value is None else str(value).strip()


def object_type(value, title):
    """HubSpot object type names are lower case and plural (contacts, companies); accept 'Contacts' too."""
    name = value.strip().lower().replace(" ", "_")
    if name not in OBJECT_TYPES and not re.match(r"^(p\d+_)?[a-z0-9_]+$|^\d-\d+$", name):
        omniscope_api.abort(f"{title} {value!r} is not a HubSpot object type, such as contacts or companies.")
    return name


def plain(value):
    """Lists and objects left after flattening become JSON text, so every field is text, number or yes/no."""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


def to_frame(data):
    df = json_normalize(data)
    for c in df.columns:
        values = df[c]
        if values.map(lambda v: isinstance(v, (list, dict))).any():
            df[c] = values.map(plain)
        elif pd.api.types.is_object_dtype(values.dtype) or pd.api.types.is_string_dtype(values.dtype):
            text = values.dropna()
            # HubSpot's timestamps (createdAt, updatedAt, date properties) become dates
            if len(text) and text.map(lambda v: isinstance(v, str) and bool(ISO_TIME.match(v))).all():
                df[c] = pd.to_datetime(values, utc=True, format="ISO8601")
    return df


omniscope_api = OmniscopeApi()

hubspot_api_key = option_text("key")
action = option_text("object")
query = option_text("params")
properties = [p.strip() for p in option_text("properties").split(",") if p.strip()] or None
from_text = option_text("from_object_type")
to_text = option_text("to_object_type")

# Parse the object_ids if provided as a comma-separated string
object_ids = [obj_id.strip() for obj_id in option_text("object_ids").split(",") if obj_id.strip()] or None

if not hubspot_api_key:
    omniscope_api.abort("Enter the private app access token (HubSpot settings > Integrations > Private apps).")

hubspot_connector = HubspotConnector(hubspot_api_key)

try:
    if action == "batch_associations":
        if not from_text or not to_text:
            omniscope_api.abort(
                "For Associations, enter both From object and To object, such as contacts and companies."
            )
        from_object_type = object_type(from_text, "From object")
        to_object_type = object_type(to_text, "To object")

        if not object_ids:
            # No IDs given: every record of the From object
            object_ids = hubspot_connector.list_object_ids(from_object_type)

        data = hubspot_connector.batch_associations(from_object_type, to_object_type, object_ids)

    elif action == "list_companies":
        data = hubspot_connector.list_companies(properties)

    elif action == "list_leads":
        data = hubspot_connector.list_leads(properties)

    elif action == "list_contacts":
        data = hubspot_connector.list_contacts(properties)

    elif action == "list_lists":
        data = hubspot_connector.list_lists()

    elif action == "list_deals":
        data = hubspot_connector.list_deals(properties)

    elif action in ("search_company", "search_contact"):
        if not query:
            omniscope_api.abort("Enter the text to search for in Search text or form ID.")
        search = hubspot_connector.search_company if action == "search_company" else hubspot_connector.search_contact
        data = search(query, properties=properties)["results"]

    elif action == "list_forms":
        data = hubspot_connector.list_forms()

    elif action == "list_form_submissions":
        # The form's ID (GUID) comes from the same option as the search text
        form_guid = query
        if not form_guid:
            omniscope_api.abort(
                "For Form submissions, enter the form's ID in Search text or form ID (the Forms action lists them)."
            )
        data = hubspot_connector.list_form_submissions(form_guid)

    else:
        omniscope_api.abort(f"Unknown action: {action}")

except (HubSpotError, requests.RequestException) as exc:
    omniscope_api.abort(str(exc))

df = to_frame(data)

if not df.empty:
    omniscope_api.write_output_records(df, 0)
    omniscope_api.close(f"Loaded {len(df):,} records.")
else:
    omniscope_api.close("HubSpot returned no records.")
