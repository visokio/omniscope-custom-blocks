"""Web Image-PDF output: saves a screenshot (PNG) of the web page at each input record's URL, and optionally one
PDF with a page per screenshot.

Chrome, driven by the visokio-omniprint package, opens each page in a window of the chosen size and saves what it
shows. The output lists the files written.
"""
import os
from urllib.parse import quote, urlsplit, urlunsplit

import pandas as pd
from omniscope.api import OmniscopeApi
from visokio_omniprint import Image, ImagesPdf

api = OmniscopeApi()

FIELDS = ["URL", "Screenshot path", "Screenshot filename", "PDF"]


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


def with_credentials(url, user, password):
    """The URL with user:password@ before the host (for Basic Authentication); path, query and #part kept."""
    if not user or not password:
        return url
    p = urlsplit(url)
    host = p.netloc.rsplit("@", 1)[-1]
    return urlunsplit((p.scheme, f"{quote(user, safe='')}:{quote(password, safe='')}@{host}", p.path, p.query,
                       p.fragment))


def hide(message, password):
    if password:
        for p in {password, quote(password, safe="")}:
            message = message.replace(p, "***")
    return message


def screen_size(resolution, orientation):
    """(width, height) in pixels of the screenshots: the resolution, turned on its side for Portrait."""
    width, height = (int(v) for v in str(resolution).lower().split("x"))
    return (height, width) if orientation == "P" else (width, height)


class SizedImage(Image):
    """visokio-omniprint's Image, with the page area of Chrome's window set to the screenshot size. (The package
    always opens a 1920x1080 window, whose page area is smaller still, whatever resolution was chosen.)"""

    def __init__(self, width, height):
        super().__init__()
        self.width, self.height = width, height

    def get_driver(self, is_docker):
        driver = super().get_driver(is_docker)
        driver.set_window_size(self.width, self.height)
        extra_w, extra_h = driver.execute_script(
            "return [window.outerWidth - window.innerWidth, window.outerHeight - window.innerHeight];")
        if extra_w or extra_h:
            driver.set_window_size(self.width + extra_w, self.height + extra_h)
        return driver


url_field = api.get_option("url_field")
folder = text(api.get_option("folder_path"))
resolution = api.get_option("resolution") or "1280x720"
orientation = api.get_option("orientation") or "L"
delay = api.get_option("sleep_seconds")
create_pdf = bool(api.get_option("create_pdf"))
pdf_name = text(api.get_option("pdf_file_name")) or "screenshots.pdf"
compressed = bool(api.get_option("compression"))
tinify = bool(api.get_option("tinify"))
tinify_key = text(api.get_option("tinify_key"))
tinify_width = api.get_option("tinify_width")
user = text(api.get_option("auth_username"))
password = api.get_option("auth_password") or ""

data = api.read_input_records(input_number=0)
if data is None:
    api.abort("Connect the records holding the web page URLs.")
if not url_field:
    api.abort("Choose the field holding the web page URLs.")
if url_field not in data.columns:
    api.abort(f"The field {url_field!r} is not in the input. Choose the field holding the web page URLs.")
if not folder:
    api.abort("Choose the output folder for the screenshots.")
if delay is None:
    delay = 3
if delay < 0:
    api.abort("The page load delay can't be negative.")
if tinify and (not tinify_key or not tinify_width or tinify_width <= 0):
    api.abort("Tinify needs an API key and an image width in pixels (or untick Tinify).")
if not pdf_name.lower().endswith(".pdf"):
    pdf_name += ".pdf"
width, height = screen_size(resolution, orientation)

try:
    os.makedirs(folder, exist_ok=True)
except OSError as exc:
    api.abort(f"Can't create the output folder {folder}: {exc}")

camera = SizedImage(width, height)
shots = []
skipped = 0
for position, (_, row) in enumerate(data.iterrows()):
    url = text(row[url_field])
    if not url:
        skipped += 1
        continue
    file_name = f"screenshot_{position}.png"
    path = os.path.join(folder, file_name)
    api.update_message(f"Screenshot of {url} ({len(shots) + 1} of {len(data) - skipped})")
    try:
        camera.grab_screenshot_in_path(with_credentials(url, user, password), delay, api.is_docker(), path)
    except Exception as exc:  # noqa: BLE001 - Chrome errors stop the block with a clear message
        api.abort(f"Could not take a screenshot of record {position + 1} ({url}): {hide(str(exc), password)}")
    shots.append({"URL": url, "Screenshot path": path, "Screenshot filename": file_name, "PDF": ""})

if create_pdf and shots:
    # The PDF is made from the full-size screenshots: one page per screenshot, the page the size of the screenshot
    pdf_path = os.path.join(folder, pdf_name)
    pages = ImagesPdf()
    for shot in shots:
        pages.add_path(shot["Screenshot path"])
    pages.create_pdf_in_path(pdf_path, orientation, resolution, compressed)
    for shot in shots:
        shot["PDF"] = pdf_path

if tinify:
    for shot in shots:
        try:
            camera.tinify(tinify_key, shot["Screenshot path"], int(tinify_width))
        except Exception as exc:  # noqa: BLE001 - the Tinify service's errors (bad key, quota) stop the block
            api.abort(f"Tinify could not shrink {shot['Screenshot filename']}: {exc}")

api.write_output_records(pd.DataFrame(shots, columns=FIELDS), output_number=0)
summary = f"{len(shots)} screenshot{'s' if len(shots) != 1 else ''} saved in {folder}"
if create_pdf and shots:
    summary += f", and {pdf_name}"
if skipped:
    summary += f"; {skipped} record{'s' if skipped != 1 else ''} without a URL skipped"
api.close(summary + ".")
