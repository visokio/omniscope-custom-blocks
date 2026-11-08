"""SharePoint Online Downloader: downloads a file, or every file in a folder, from a SharePoint Online document library
to the Omniscope server through Microsoft Graph, and lists the downloaded files for an Append files block.

Signs in as an app registered in Microsoft Entra ID (client ID and secret) with the Microsoft Graph application
permission Sites.Read.All or Sites.Selected."""
import base64
import os
from urllib.parse import quote, unquote, urlparse

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

GRAPH = "https://graph.microsoft.com/v1.0"
LOGIN = "https://login.microsoftonline.com"
TIMEOUT = 60

omniscope_api = OmniscopeApi()


def option_text(name):
    value = omniscope_api.get_option(name)
    return str(value).strip() if value is not None else ""


tenant = option_text("tenantId")
client_id = option_text("clientId")
client_secret = omniscope_api.get_option("clientSecret") or ""
file_url = option_text("fileUrl")
local_folder = option_text("localFolder")

for value, label in ((tenant, "Tenant ID"), (client_id, "Client ID"), (client_secret, "Client secret"),
                     (file_url, "File or folder URL")):
    if not value:
        omniscope_api.abort(f"Enter the {label}.")
if not file_url.lower().startswith("https://"):
    omniscope_api.abort(f"The URL must start with https://, got: {file_url}")

session = requests.Session()


class GraphError(Exception):
    pass


def check(response, what):
    if response.ok:
        return response
    try:
        detail = response.json().get("error", {})
        detail = detail.get("message") if isinstance(detail, dict) else response.json().get("error_description")
    except ValueError:
        detail = response.text[:300]
    hint = ""
    if response.status_code in (401, 403):
        hint = (" Check that the app has the Microsoft Graph application permission Sites.Read.All (or Sites.Selected "
                "with access to this site) and that an administrator has granted consent.")
    elif response.status_code == 404:
        hint = " Check the URL: open it in a browser and copy the address of the file or folder."
    raise GraphError(f"{what} failed ({response.status_code}): {detail}.{hint}")


def sign_in():
    response = session.post(f"{LOGIN}/{quote(tenant)}/oauth2/v2.0/token", timeout=TIMEOUT, data={
        "grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"})
    if not response.ok:
        try:
            detail = response.json().get("error_description", "").splitlines()[0]
        except (ValueError, IndexError):
            detail = response.text[:300]
        raise GraphError(f"Sign-in to Microsoft Entra ID failed ({response.status_code}): {detail} "
                         f"Check the tenant ID, client ID and client secret (secrets expire).")
    session.headers["Authorization"] = "Bearer " + response.json()["access_token"]


def get(url, what, **kw):
    return check(session.get(url, timeout=TIMEOUT, **kw), what)


def find_item(url):
    """The drive item for a SharePoint URL: the library is matched against the site's document libraries."""
    parsed = urlparse(url)
    path = unquote(parsed.path).rstrip("/")
    segments = [s for s in path.split("/") if s]
    # Links copied from the browser such as /:x:/r/sites/... and sharing links such as /:x:/s/site/AbCd...
    if segments and len(segments[0]) == 3 and segments[0].startswith(":") and segments[0].endswith(":"):
        if len(segments) > 1 and segments[1] == "r":
            segments = segments[2:]
            path = "/" + "/".join(segments)
        else:
            token = "u!" + base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
            return get(f"{GRAPH}/shares/{token}/driveItem", "Opening the sharing link").json()
    site_path = "/".join(segments[:2]) if segments[:1] in (["sites"], ["teams"]) else ""
    site_url = f"{GRAPH}/sites/{parsed.hostname}" + (f":/{site_path}" if site_path else "")
    site = get(site_url, f"Finding the site {parsed.hostname}/{site_path}").json()
    drives = get(f"{GRAPH}/sites/{site['id']}/drives", "Listing the site's document libraries").json()["value"]
    best = None
    for drive in drives:
        drive_path = unquote(urlparse(drive.get("webUrl", "")).path).rstrip("/")
        if (path == drive_path or path.startswith(drive_path + "/")) and (best is None or len(drive_path) > best[1]):
            best = (drive, len(drive_path))
    if best is None:
        names = ", ".join(d.get("name", "?") for d in drives)
        raise GraphError(f"The URL is not in one of the site's document libraries ({names}).")
    drive, length = best
    relative = path[length:].strip("/")
    if not relative:
        return get(f"{GRAPH}/drives/{drive['id']}/root", "Opening the library").json()
    return get(f"{GRAPH}/drives/{drive['id']}/root:/{quote(relative)}", f"Finding {relative}").json()


def download(item, folder):
    drive_id = item["parentReference"]["driveId"]
    target = os.path.join(folder, item["name"])
    response = get(f"{GRAPH}/drives/{drive_id}/items/{item['id']}/content", f"Downloading {item['name']}",
                   stream=True)
    with open(target, "wb") as fh:
        for chunk in response.iter_content(chunk_size=1 << 20):
            fh.write(chunk)
    return {"File path": target, "File name": item["name"], "Size (bytes)": item.get("size"),
            "Modified": item.get("lastModifiedDateTime"), "SharePoint URL": item.get("webUrl")}


# Empty: the block's own working folder on the Omniscope server, as in earlier versions of the block.
local_folder = local_folder or os.path.dirname(os.path.realpath(__file__))
os.makedirs(local_folder, exist_ok=True)

rows = []
try:
    omniscope_api.update_message("Signing in to Microsoft Graph")
    sign_in()
    item = find_item(file_url)
    if "folder" in item:
        drive_id = item["parentReference"]["driveId"]
        children = []
        next_url = f"{GRAPH}/drives/{drive_id}/items/{item['id']}/children"
        while next_url:
            page = get(next_url, f"Listing {item['name']}").json()
            children.extend(page.get("value", []))
            next_url = page.get("@odata.nextLink")
        files = sorted((c for c in children if "file" in c), key=lambda c: c["name"].lower())
        for number, child in enumerate(files, start=1):
            omniscope_api.update_message(f"Downloading {number} of {len(files)}: {child['name']}")
            rows.append(download(child, local_folder))
    else:
        omniscope_api.update_message(f"Downloading {item['name']}")
        rows.append(download(item, local_folder))
except GraphError as error:
    omniscope_api.abort(str(error))
except requests.RequestException as error:
    omniscope_api.abort(f"Could not reach Microsoft 365: {error}")

output = pd.DataFrame(rows, columns=["File path", "File name", "Size (bytes)", "Modified", "SharePoint URL"])
output["Size (bytes)"] = output["Size (bytes)"].astype("Int64")
output["Modified"] = pd.to_datetime(output["Modified"], utc=True).dt.tz_localize(None)
omniscope_api.write_output_records(output, output_number=0)
omniscope_api.commit(f"Downloaded {len(output)} file(s) to {local_folder}.")
