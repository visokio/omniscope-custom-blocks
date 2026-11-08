"""Slack Bot: posts one message to a Slack channel for each input record, optionally with a file attached.

Messages go through Slack's Web API as the app's bot user: chat.postMessage for text, and the three-step external
upload (files.getUploadURLExternal, the file's bytes, files.completeUploadExternal) for a message with a file.
"""
import json
import os
import re
from urllib.parse import quote

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

API = "https://slack.com/api/"
TIMEOUT = 60
HINTS = {
    "invalid_auth": "check the Bot User OAuth token (it starts with xoxb-)",
    "not_authed": "enter the Bot User OAuth token",
    "token_revoked": "the token was revoked: copy the current one from the app's OAuth & Permissions page",
    "channel_not_found": "check the channel ID (in the channel's details; it starts with C, or G for an older "
                         "private channel), and that the app has been added to a private channel",
    "not_in_channel": "add the app to the channel (in the channel, /invite @your-app)",
    "missing_scope": "the app needs the chat:write scope, and files:write to attach files",
    "is_archived": "the channel is archived",
    "ratelimited": "Slack's rate limit was reached; post fewer messages per run",
}
MESSAGE_FIELDS = ["Row", "Message", "AttachmentPath"]
SENT_FIELDS = ["Row", "Action", "Channel", "Timestamp", "File ID"]


class SlackError(Exception):
    pass


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
            out.append(f"<{quote(token, safe=':/?#[]@!$&()*+,;=%~')}|{escape(token)}>{escape(trail)}")
        pos = match.end()
    out.append(escape(message[pos:]))
    return "".join(out)


def check(response, step):
    if not response.ok:
        raise SlackError(f"{step}: HTTP {response.status_code}")
    data = response.json()
    if not data.get("ok", False):
        code = data.get("error", "unknown_error")
        raise SlackError(f"{step}: {code}" + (f" ({HINTS[code]})" if code in HINTS else ""))
    return data


def post_message(channel, message, token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    payload = json.dumps({"channel": channel, "text": message})
    return check(requests.post(API + "chat.postMessage", data=payload, headers=headers, timeout=TIMEOUT),
                 "chat.postMessage")


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


api = OmniscopeApi()
message_opt = api.get_option("message")
attach_opt = text(api.get_option("attachmentPath"))
attach_name_opt = text(api.get_option("attachmentName"))
channel = text(api.get_option("channelID"))
token = text(api.get_option("authToken"))

data = api.read_input_records(input_number=0)
if data is None:
    api.abort("Connect the records holding the messages to send.")
if not token:
    api.abort("Enter the Bot User OAuth token (from the Slack app's OAuth & Permissions page).")
if not channel:
    api.abort("Enter the ID of the channel to post to (in the channel's details, such as C0123ABCD).")
if not message_opt:
    api.abort("Choose the field holding the messages.")


def value(row, option):
    """The option is a field of the input (each record's value) or, if not, the text itself (the same for all)."""
    return text(row[option]) if option and option in data.columns else text(option)


messages, sent = [], []
for position, (index, row) in enumerate(data.iterrows()):
    message = slack_text(value(row, message_opt))
    attachment = value(row, attach_opt)
    title = value(row, attach_name_opt)
    messages.append({"Row": index, "Message": message, "AttachmentPath": attachment})
    if not message and not attachment:
        sent.append({"Row": index, "Action": "skip"})
        continue
    try:
        if attachment:
            if not os.path.isfile(attachment):
                raise SlackError(f"the file to attach was not found: {attachment}")
            api.update_message(f"Posting record {position + 1} of {len(data)} with {os.path.basename(attachment)}")
            file_id = upload_file(channel, message, attachment, token, title)
            sent.append({"Row": index, "Action": "upload_with_comment", "Channel": channel, "File ID": file_id})
        else:
            api.update_message(f"Posting record {position + 1} of {len(data)}")
            reply = post_message(channel, message, token)
            sent.append({"Row": index, "Action": "postMessage", "Channel": reply.get("channel", channel),
                         "Timestamp": reply.get("ts")})
    except (SlackError, requests.RequestException) as exc:
        posted = sum(1 for s in sent if s["Action"] != "skip")
        api.abort(f"Record {position + 1} was not posted: {exc}. "
                  f"{posted} message{'s were' if posted != 1 else ' was'} posted before it.")

api.write_output_records(pd.DataFrame(messages, columns=MESSAGE_FIELDS), output_number=0)
api.write_output_records(pd.DataFrame(sent, columns=SENT_FIELDS), output_number=1)
posted = sum(1 for s in sent if s["Action"] != "skip")
api.close(f"{posted} message{'s' if posted != 1 else ''} posted to {channel}.")
