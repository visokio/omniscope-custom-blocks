"""Report to PowerPoint: takes a screenshot of each Report tab (or other web page) in the input and makes a
PowerPoint file with one slide per screenshot.

Chrome, driven by the visokio-omniprint package, opens each page in a window of the chosen size; python-pptx
builds the slides, each the shape of the screenshots and filled by one.
"""
import os
from urllib.parse import quote, urlsplit, urlunsplit

import pandas as pd
from omniscope.api import OmniscopeApi
from pptx import Presentation
from visokio_omniprint import Image

api = OmniscopeApi()

FIELDS = ["URL", "Screenshot path", "Screenshot filename", "PowerPoint file"]
LONG_SIDE = 12192000  # 13.333 inches in EMU: the long side of PowerPoint's 16:9 widescreen slide


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
file_name = text(api.get_option("output_file_name")) or "report.pptx"
tinify = bool(api.get_option("tinify"))
tinify_key = text(api.get_option("tinify_key"))
tinify_width = api.get_option("tinify_width")
user = text(api.get_option("auth_username"))
password = api.get_option("auth_password") or ""

data = api.read_input_records(input_number=0)
if data is None:
    api.abort("Connect the records holding the Report tab URLs (for example from a Project metadata block).")
if not url_field:
    api.abort("Choose the field holding the Report tab URLs.")
if url_field not in data.columns:
    api.abort(f"The field {url_field!r} is not in the input. Choose the field holding the Report tab URLs.")
if not folder:
    api.abort("Choose the output folder for the PowerPoint file.")
if delay is None:
    delay = 3
if delay < 0:
    api.abort("The page load delay can't be negative.")
if tinify and (not tinify_key or not tinify_width or tinify_width <= 0):
    api.abort("Tinify needs an API key and an image width in pixels (or untick Tinify).")
if not file_name.lower().endswith(".pptx"):
    file_name += ".pptx"
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
    png_name = f"screenshot_{position}.png"
    path = os.path.join(folder, png_name)
    api.update_message(f"Screenshot of {url} ({len(shots) + 1} of {len(data) - skipped})")
    try:
        camera.grab_screenshot_in_path(with_credentials(url, user, password), delay, api.is_docker(), path)
        if tinify:
            camera.tinify(tinify_key, path, int(tinify_width))
    except Exception as exc:  # noqa: BLE001 - Chrome and Tinify errors stop the block with a clear message
        api.abort(f"Could not take a screenshot of record {position + 1} ({url}): {hide(str(exc), password)}")
    shots.append({"URL": url, "Screenshot path": path, "Screenshot filename": png_name})

pptx_path = ""
if shots:
    # Slides the shape of the screenshots (the long side 13.333 inches), each filled by one screenshot
    deck = Presentation()
    if width >= height:
        deck.slide_width, deck.slide_height = LONG_SIDE, round(LONG_SIDE * height / width)
    else:
        deck.slide_width, deck.slide_height = round(LONG_SIDE * width / height), LONG_SIDE
    blank = deck.slide_layouts[6]
    for shot in shots:
        slide = deck.slides.add_slide(blank)
        slide.shapes.add_picture(shot["Screenshot path"], 0, 0, deck.slide_width, deck.slide_height)
    pptx_path = os.path.join(folder, file_name)
    deck.save(pptx_path)

output = pd.DataFrame(shots, columns=FIELDS[:3])
output["PowerPoint file"] = pptx_path
api.write_output_records(output, output_number=0)
if shots:
    summary = f"{file_name} written to {folder} with {len(shots)} slide{'s' if len(shots) != 1 else ''}"
else:
    summary = "No URLs in the input: no PowerPoint file written"
if skipped:
    summary += f"; {skipped} record{'s' if skipped != 1 else ''} without a URL skipped"
api.close(summary + ".")
