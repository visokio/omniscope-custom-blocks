"""Multi-tenant Report to PDF: prints one Report tab once per scenario of a multi-tenant configuration.

For each input record the scenario's version of the tab ('.../r/Report/s/<scenario>/') is opened in Omniscope's
print mode by Chrome, driven by the visokio-omniprint package, and saved as '<Report>-<scenario>.pdf' in the
output folder. The output lists the files written.
"""
import os
import re
from urllib.parse import quote, unquote, urlsplit

import pandas as pd
from omniscope.api import OmniscopeApi
from visokio_omniprint import Pdf

api = OmniscopeApi()

FIELDS = ["Scenario", "URL", "PDF filename", "PDF path"]


def text(value):
    """A cell or option value as trimmed text; empty for a missing value."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def split_report_url(url):
    """Split a Report address into (address of the report, query, tab part after '#', report name).

    Accepts the address with or without the '/' before '#'."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    path = parts.path.rstrip("/")
    segments = [unquote(s) for s in path.split("/") if s]
    host = parts.netloc.rsplit("@", 1)[-1]
    return f"{parts.scheme}://{host}{path}", parts.query, parts.fragment, segments[-1] if segments else host


def with_credentials(address, user, password):
    """The address with user:password@ before the host (for Basic Authentication), or unchanged."""
    if not user or not password:
        return address
    scheme, rest = address.split("://", 1)
    return f"{scheme}://{quote(user, safe='')}:{quote(password, safe='')}@{rest}"


def hide(message, password):
    """An error text with the password masked, in case it quotes the address."""
    if password:
        for p in {password, quote(password, safe="")}:
            message = message.replace(p, "***")
    return message


def safe_file_name(name):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .")
    return name or "report"


def page_size(width, height):
    size = ""
    if width is not None and width > 0:
        size += f"&pageWidth={int(width)}"
    if height is not None and height > 0:
        size += f"&pageHeight={int(height)}"
    return size


base_url = text(api.get_option("report"))
scenario_field = api.get_option("scenarioField") or "scenario"
folder = text(api.get_option("outputFolder"))
page_width = api.get_option("pageWidth")
page_height = api.get_option("pageHeight")
delay = api.get_option("chromeDelay")
user = text(api.get_option("auth_username"))
password = api.get_option("auth_password") or ""

data = api.read_input_records(input_number=0)
if data is None:
    api.abort("Connect the multi-tenant configuration: one record per scenario to print.")
if scenario_field not in data.columns:
    api.abort(f"The input has no field {scenario_field!r}. Choose the field holding the scenario IDs.")
if not base_url:
    api.abort("Enter the address of the Report tab to print (copy it from the browser's address bar).")
parts = split_report_url(base_url)
if parts is None:
    api.abort(f"{base_url!r} is not a web address (http:// or https://).")
address, query, tab, report_name = parts
if "/s/" in address.split("/r/", 1)[-1] + "/":
    api.abort("Enter the Report tab address without a scenario ('/s/...'); the block adds each scenario itself.")
if not folder:
    api.abort("Choose the output folder for the PDF files.")
if delay is None:
    delay = 3
if delay < 0:
    api.abort("The Chrome loading delay can't be negative.")
size = page_size(page_width, page_height)

try:
    os.makedirs(folder, exist_ok=True)
except OSError as exc:
    api.abort(f"Can't create the output folder {folder}: {exc}")

printer = Pdf()
written = []
used = set()
skipped = 0
for position, (_, row) in enumerate(data.iterrows()):
    scenario = text(row[scenario_field])
    if not scenario:
        skipped += 1
        continue
    scenario_path = f"/s/{quote(scenario, safe='')}/" + (f"?{query}" if query else "")
    after_hash = f"#device=printer{size}" + (f"&tab={tab}" if tab else "")
    url = address + scenario_path + (f"#{tab}" if tab else "")
    print_url = with_credentials(address, user, password) + scenario_path + after_hash

    name = safe_file_name(f"{report_name}-{scenario}")
    file_name, n = f"{name}.pdf", 1
    while file_name.lower() in used:
        n += 1
        file_name = f"{name}-{n}.pdf"
    used.add(file_name.lower())
    path = os.path.join(folder, file_name)

    api.update_message(f"Printing scenario {scenario} ({len(written) + 1} of {len(data) - skipped})")
    try:
        content = printer.create_pdf(print_url, delay, api.is_docker())
        with open(path, "wb") as fh:
            fh.write(content)
    except Exception as exc:  # noqa: BLE001 - Chrome and file errors alike stop the block with a clear message
        api.abort(f"Could not print scenario {scenario!r} (record {position + 1}): {hide(str(exc), password)}")
    written.append({"Scenario": scenario, "URL": url, "PDF filename": file_name, "PDF path": path})

api.write_output_records(pd.DataFrame(written, columns=FIELDS), output_number=0)
summary = f"{len(written)} PDF file{'s' if len(written) != 1 else ''} written to {folder}"
if skipped:
    summary += f"; {skipped} record{'s' if skipped != 1 else ''} without a scenario skipped"
api.close(summary + ".")
