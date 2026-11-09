"""Send Report to Slack: takes a screenshot of the Report tab (or other web page) at each input record's URL and
posts it to a Slack channel with the record's message and the link; optionally also one PDF of all screenshots.

Chrome, driven by the visokio-omniprint package, takes the screenshots in a window of the chosen size. Files go to
Slack through its Web API as the app's bot user (files.getUploadURLExternal, the file's bytes,
files.completeUploadExternal).
"""
import json
import os
import re
import shutil
import tempfile
from urllib.parse import quote, urlsplit, urlunsplit

import pandas as pd
import requests
from omniscope.api import OmniscopeApi
from visokio_omniprint import Image, ImagesPdf

API = "https://slack.com/api/"
TIMEOUT = 60
HINTS = {
    "invalid_auth": "check the Bot User OAuth token (it starts with xoxb-)",
    "not_authed": "enter the Bot User OAuth token",
    "token_revoked": "the token was revoked: copy the current one from the app's OAuth & Permissions page",
    "channel_not_found": "check the channel ID (in the channel's details; it starts with C, or G for an older "
                         "private channel), and that the app has been added to a private channel",
    "not_in_channel": "add the app to the channel (in the channel, /invite @your-app)",
    "missing_scope": "the app needs the files:write scope",
    "is_archived": "the channel is archived",
    "ratelimited": "Slack's rate limit was reached; post fewer screenshots per run",
}
RESULT_FIELDS = ["Row", "Status", "SlackFileId"]
ERROR_FIELDS = ["Row", "Error"]


class SlackError(Exception):
    """A record that could not be posted (Slack's refusal, or the screenshot before it)."""


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


# Slack markup already in the text (<https://...|label>, <@U123>, <#C123>, <!here>) is kept as it is
SLACK_MARKUP = r"<(?:https?://|mailto:|[@#!])[^<>\n]*>"
LINK = re.compile(SLACK_MARKUP + r"|https?://[^\s<>]+")


def escape(part):
    return part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def link(url):
    return f"<{quote(url, safe=':/?#[]@!$&()*+,;=%~')}|{escape(url)}>"


def slack_text(message):
    """The message in Slack's text format: &, < and > escaped, and each web address made a link that ends at the
    first space (punctuation just after it, such as a full stop, stays outside the link)."""
    out, pos = [], 0
    for match in LINK.finditer(message):
        out.append(escape(message[pos:match.start()]))
        token = match.group(0)
        if token.startswith("<"):
            out.append(token)
        else:
            trail = ""
            while token[-1] in ".,;:!?)'\"" and not (token[-1] == ")" and token.count("(") >= token.count(")")):
                trail, token = token[-1] + trail, token[:-1]
            out.append(link(token) + escape(trail))
        pos = match.end()
    out.append(escape(message[pos:]))
    return "".join(out)


def comment_for(message, url):
    """The message followed by the Report's link, unless the message already holds it. The link is the address
    as given (it may hold spaces), never the one with the login added."""
    if url in message:
        before, _, after = message.partition(url)
        return slack_text(before) + link(url) + slack_text(after)
    return (slack_text(message) + "\n" if message else "") + link(url)


def check(response, step):
    if not response.ok:
        raise SlackError(f"{step}: HTTP {response.status_code}")
    data = response.json()
    if not data.get("ok", False):
        code = data.get("error", "unknown_error")
        raise SlackError(f"{step}: {code}" + (f" ({HINTS[code]})" if code in HINTS else ""))
    return data


def upload_file(channel, comment, path, token, title):
    """Upload a file and share it to the channel with the message: one post holding both."""
    headers = {"Authorization": f"Bearer {token}"}
    name = os.path.basename(path)
    step1 = check(requests.post(API + "files.getUploadURLExternal", headers=headers, timeout=TIMEOUT,
                                files={"filename": (None, name), "length": (None, str(os.path.getsize(path)))}),
                  "files.getUploadURLExternal")
    with open(path, "rb") as fh:
        uploaded = requests.post(step1["upload_url"], data=fh, timeout=TIMEOUT,
                                 headers={"Content-Type": "application/octet-stream"})
    if not uploaded.ok:
        raise SlackError(f"uploading {name}: HTTP {uploaded.status_code}")
    files = json.dumps([{"id": step1["file_id"], "title": title or name}])
    check(requests.post(API + "files.completeUploadExternal", headers=headers, timeout=TIMEOUT,
                        files={"files": (None, files), "channel_id": (None, channel),
                               "initial_comment": (None, comment)}),
          "files.completeUploadExternal")
    return step1["file_id"]


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


api = OmniscopeApi()
url_field = api.get_option("url_field")
delay = api.get_option("sleep_seconds")
resolution = api.get_option("resolution") or "1280x720"
orientation = api.get_option("orientation") or "L"
create_pdf = bool(api.get_option("create_pdf"))
compressed = bool(api.get_option("compression"))
tinify = bool(api.get_option("tinify"))
tinify_key = text(api.get_option("tinify_key"))
tinify_width = api.get_option("tinify_width")
user = text(api.get_option("auth_username"))
password = api.get_option("auth_password") or ""
channel = text(api.get_option("channelID"))
token = text(api.get_option("authToken"))
message_opt = api.get_option("message")

data = api.read_input_records(input_number=0)
if data is None:
    api.abort("Connect the records holding the Report URLs and messages.")
if not url_field:
    api.abort("Choose the field holding the Report URLs.")
if url_field not in data.columns:
    api.abort(f"The field {url_field!r} is not in the input. Choose the field holding the Report URLs.")
if not token:
    api.abort("Enter the Bot User OAuth token (from the Slack app's OAuth & Permissions page).")
if not channel:
    api.abort("Enter the ID of the channel to post to (in the channel's details, such as C0123ABCD).")
if delay is None:
    delay = 3
if delay < 0:
    api.abort("The page load delay can't be negative.")
if tinify and (not tinify_key or not tinify_width or tinify_width <= 0):
    api.abort("Tinify needs an API key and an image width in pixels (or untick Tinify).")
width, height = screen_size(resolution, orientation)

camera = SizedImage(width, height)
pages = ImagesPdf()
results, errors, shots = [], [], []
working_dir = tempfile.mkdtemp(prefix="omniscope_reports_")
try:
    for position, (index, row) in enumerate(data.iterrows()):
        url = text(row[url_field])
        if not url:
            results.append({"Row": index, "Status": "skipped"})
            continue
        message = text(row[message_opt]) if message_opt in data.columns else text(message_opt)
        api.update_message(f"Screenshot of {url} ({position + 1} of {len(data)})")
        try:
            path = os.path.join(working_dir, f"screenshot_{index}.png")
            try:
                camera.grab_screenshot_in_path(with_credentials(url, user, password), delay, api.is_docker(), path)
            except Exception as exc:  # noqa: BLE001 - Chrome errors are reported per record
                raise SlackError(f"screenshot failed: {hide(str(exc), password)}") from None
            if tinify:
                try:
                    camera.tinify(tinify_key, path, int(tinify_width))
                except Exception as exc:  # noqa: BLE001 - the Tinify service's errors (bad key, quota)
                    raise SlackError(f"Tinify could not shrink the screenshot: {exc}") from None
            shots.append(path)
            pages.add_path(path)
            file_id = upload_file(channel, comment_for(message, url), path, token, "Omniscope Report")
            results.append({"Row": index, "Status": "posted", "SlackFileId": file_id})
        except (SlackError, requests.RequestException, OSError) as exc:
            errors.append({"Row": index, "Error": str(exc)})
            results.append({"Row": index, "Status": "error"})

    if create_pdf and shots:
        try:
            pdf_path = os.path.join(working_dir, "report.pdf")
            pages.create_pdf_in_path(pdf_path, orientation, resolution, compressed)
            upload_file(channel, "Combined PDF snapshot", pdf_path, token, "Omniscope Report PDF")
        except (SlackError, requests.RequestException, OSError) as exc:
            errors.append({"Row": "PDF", "Error": str(exc)})
finally:
    shutil.rmtree(working_dir, ignore_errors=True)

posted = sum(1 for r in results if r["Status"] == "posted")
if errors and not posted:
    # Nothing reached Slack: stop, so that a scheduled run shows as failed
    api.abort(f"Nothing was posted. Record {errors[0]['Row']}: {errors[0]['Error']}")

errors_out = pd.DataFrame(errors, columns=ERROR_FIELDS)
errors_out["Row"] = errors_out["Row"].astype(str)
api.write_output_records(pd.DataFrame(results, columns=RESULT_FIELDS), output_number=0)
api.write_output_records(errors_out, output_number=1)
summary = f"{posted} screenshot{'s' if posted != 1 else ''} posted to {channel}"
if errors:
    summary += f"; {len(errors)} error{'s' if len(errors) != 1 else ''} (see the Errors output)"
api.close(summary + ".")
