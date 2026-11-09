"""Report tab to PDF: prints the Report tab whose address is in each input record to a PDF file.

Chrome, driven by the visokio-omniprint package, opens each tab in Omniscope's print mode and saves the page as
a PDF in the output folder. The output lists the files written.
"""
import os
import re
from urllib.parse import quote, unquote, urlsplit

import pandas as pd
from omniscope.api import OmniscopeApi
from visokio_omniprint import Pdf

api = OmniscopeApi()

FIELDS = ["URL", "PDF filename", "PDF path"]


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
    """Split a Report address into (address of the report or scenario, query, tab part after '#', name for files).

    Accepts the address with or without the '/' before '#': '.../Project.iox/r/Report/#Tab' and
    '.../Project.iox/r/Report#Tab' are the same tab."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    path = parts.path.rstrip("/")
    segments = [unquote(s) for s in path.split("/") if s]
    if "r" in segments:
        after = segments[len(segments) - 1 - segments[::-1].index("r") + 1:]
        name = "-".join(s for s in after if s != "s") or segments[-1]
    else:
        name = segments[-1] if segments else parts.netloc
    host = parts.netloc.rsplit("@", 1)[-1]
    return f"{parts.scheme}://{host}{path}", parts.query, parts.fragment, name


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


url_field = api.get_option("report")
name_field = api.get_option("fileName")
folder = text(api.get_option("outputFolder"))
page_width = api.get_option("pageWidth")
page_height = api.get_option("pageHeight")
delay = api.get_option("chromeDelay")
user = text(api.get_option("auth_username"))
password = api.get_option("auth_password") or ""

data = api.read_input_records(input_number=0)
if data is None:
    api.abort("Connect the records holding the Report tab URLs (for example from a Project metadata block).")
if not url_field:
    api.abort("Choose the field holding the Report tab URLs.")
if url_field not in data.columns:
    api.abort(f"The field {url_field!r} is not in the input. Choose the field holding the Report tab URLs.")
if name_field and name_field not in data.columns:
    api.abort(f"The file name field {name_field!r} is not in the input.")
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
    url = text(row[url_field])
    if not url:
        skipped += 1
        continue
    parts = split_report_url(url)
    if parts is None:
        api.abort(f"Record {position + 1}: {url!r} is not a web address (http:// or https://).")
    address, query, tab, report_name = parts

    print_url = with_credentials(address, user, password) + "/" + (f"?{query}" if query else "")
    print_url += f"#device=printer{size}" + (f"&tab={tab}" if tab else "")

    name = text(row[name_field]) if name_field else ""
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    if not name:
        tab_name = unquote(tab.split("&", 1)[0]) if tab else ""
        name = f"{report_name}-{tab_name}-{position}" if tab_name else f"{report_name}-{position}"
    name = safe_file_name(name)
    file_name, n = f"{name}.pdf", 1
    while file_name.lower() in used:
        n += 1
        file_name = f"{name}-{n}.pdf"
    used.add(file_name.lower())
    path = os.path.join(folder, file_name)

    api.update_message(f"Printing {url} ({len(written) + 1} of {len(data) - skipped})")
    try:
        content = printer.create_pdf(print_url, delay, api.is_docker())
        with open(path, "wb") as fh:
            fh.write(content)
    except Exception as exc:  # noqa: BLE001 - Chrome and file errors alike stop the block with a clear message
        api.abort(f"Could not print record {position + 1} ({url}): {hide(str(exc), password)}")
    written.append({"URL": url, "PDF filename": file_name, "PDF path": path})

api.write_output_records(pd.DataFrame(written, columns=FIELDS), output_number=0)
summary = f"{len(written)} PDF file{'s' if len(written) != 1 else ''} written to {folder}"
if skipped:
    summary += f"; {skipped} record{'s' if skipped != 1 else ''} without a URL skipped"
api.close(summary + ".")
