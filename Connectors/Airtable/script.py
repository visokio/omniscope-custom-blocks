from omniscope.api import OmniscopeApi
import pandas as pd
import requests
import json

omniscope_api = OmniscopeApi()

token = omniscope_api.get_option("token")
base_id = omniscope_api.get_option("base_id")
table = omniscope_api.get_option("table")
page_size = omniscope_api.get_option("page_size") or 100

if not token or not base_id or not table:
    omniscope_api.abort("Token, Base ID and Table are required")

# ensure page_size within 1-100
try:
    page_size = int(page_size)
except Exception:
    page_size = 100
if page_size <= 0 or page_size > 100:
    page_size = 100

url = f"https://api.airtable.com/v0/{base_id}/{table}"
headers = {"Authorization": f"Bearer {token}"}
params = {"pageSize": page_size}
records = []

try:
    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            omniscope_api.abort(f"Request failed: {response.status_code} {response.text}")
        data = response.json()
        for rec in data.get("records", []):
            fields = rec.get("fields", {}).copy()
            fields["id"] = rec.get("id")
            records.append(fields)
        offset = data.get("offset")
        if offset:
            params["offset"] = offset
        else:
            break
except Exception as e:
    omniscope_api.abort(str(e))

df = pd.DataFrame(records)


def serialise(value):
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return value

if not df.empty:
    df = df.applymap(serialise)
    omniscope_api.write_output_records(df, 0)
    omniscope_api.close()
else:
    omniscope_api.close("No data retrieved")
