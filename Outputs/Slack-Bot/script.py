from omniscope.api import OmniscopeApi
import json, pandas as pd, requests, os
import re, time
from urllib.parse import quote


def slack_api_get(url, params, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = requests.get(url, params=params, headers=headers)
    if not r.ok:
        raise Exception(f"Slack HTTP error {r.status_code}: {r.text}")
    data = r.json()
    if not data.get("ok", False):
        raise Exception(f"Slack API error {data.get('error')}: {data}")
    return data

def slackify_links(text):
    if not text:
        return text
    url_pattern = r'(https?://[^\s]+(?: [^\s]+)*)'
    def repl(match):
        raw_url = match.group(0)
        encoded = quote(raw_url, safe=':/?=&%#.')
        return f"<{encoded}|{raw_url}>"
    return re.sub(url_pattern, repl, text)

omniscope_api = OmniscopeApi()

postMessageUrl = "https://slack.com/api/chat.postMessage"

def slack_post_json(url, payload, auth_token):
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    r = requests.post(url, data=json.dumps(payload), headers=headers)
    if not r.ok:
        raise Exception(f"Slack HTTP error {r.status_code}: {r.text}")
    data = r.json()
    if not data.get("ok", False):
        raise Exception(f"Slack API error {data.get('error')}: {data}")
    return data

def slack_upload_file_with_comment(channel_id, initial_comment, file_path, auth_token, display_name):
    """
    Uploads a file and posts it into a channel with initial_comment.
    This results in ONE channel post that contains the attachment + message.
    Slack Web API flow:
      1) files.getUploadURLExternal
      2) POST bytes to upload_url
      3) files.completeUploadExternal (share to channel + initial_comment)
    """
    file_path = (str(file_path) if file_path is not None else "").strip()
    if not file_path:
        raise Exception("Attachment file path is empty.")
    if not os.path.isfile(file_path):
        raise Exception(f"Attachment file not found: {file_path}")

    filename = os.path.basename(file_path)
    title = display_name if display_name else filename    
    length = os.path.getsize(file_path)

    headers_auth = {"Authorization": f"Bearer {auth_token}"}

    # 1) Get upload URL + file_id
    r1 = requests.post(
        "https://slack.com/api/files.getUploadURLExternal",
        headers=headers_auth,
        files={
            "filename": (None, filename),
            "length": (None, str(length)),
        },
    )
    if not r1.ok:
        raise Exception(f"Slack HTTP error {r1.status_code}: {r1.text}")
    data1 = r1.json()
    if not data1.get("ok", False):
        raise Exception(f"Slack API error {data1.get('error')}: {data1}")

    upload_url = data1["upload_url"]
    file_id = data1["file_id"]

    # 2) Upload raw bytes
    with open(file_path, "rb") as f:
        r2 = requests.post(upload_url, headers={"Content-Type": "application/octet-stream"}, data=f)
    if not r2.ok:
        raise Exception(f"Upload bytes failed {r2.status_code}: {r2.text}")

    # 3) Complete + share to channel with initial_comment
    files_payload = json.dumps([{"id": file_id, "title": title}])
    r3 = requests.post(
        "https://slack.com/api/files.completeUploadExternal",
        headers=headers_auth,
        files={
            "files": (None, files_payload),
            "channel_id": (None, channel_id),
            "initial_comment": (None, initial_comment or ""),
        },
    )
    if not r3.ok:
        raise Exception(f"Slack HTTP error {r3.status_code}: {r3.text}")
    data3 = r3.json()
    if not data3.get("ok", False):
        raise Exception(f"Slack API error {data3.get('error')}: {data3}")

    return data3


messagesToSend = []
responses = []

input_data = omniscope_api.read_input_records(input_number=0)
input_data.fillna("", inplace=True)

# These options should be column names OR literal values (same for all rows)
message_opt = omniscope_api.get_option("message")
attach_opt   = omniscope_api.get_option("attachmentPath")
attach_name_opt = omniscope_api.get_option("attachmentName")


channel_id = omniscope_api.get_option("channelID")
authToken = omniscope_api.get_option("authToken")


for idx, row in input_data.iterrows():
    # resolve message (column or literal)
    msg_val = row[message_opt] if message_opt in input_data.columns else message_opt
    message = (str(msg_val) if msg_val is not None else "").strip()
    message = slackify_links(message)

    # resolve file path (column or literal)
    attach_val = row[attach_opt] if attach_opt in input_data.columns else attach_opt
    attach_path = (str(attach_val) if attach_val is not None else "").strip()
    
    name_val = row[attach_name_opt] if attach_name_opt in input_data.columns else attach_name_opt
    attach_display_name = (str(name_val) if name_val is not None else "").strip()

    messagesToSend.append({"Row": idx, "Message": message, "AttachmentPath": attach_path})

    if not message and not attach_path:
        responses.append({"Row": idx, "Action": "skip"})
        continue

    if attach_path:
        resp = slack_upload_file_with_comment(channel_id, message, attach_path, authToken, attach_display_name)
        responses.append({"Row": idx, "Action": "upload_with_comment", "Response": resp})
    else:
        resp = slack_post_json(postMessageUrl, {"channel": channel_id, "text": message}, authToken)
        responses.append({"Row": idx, "Action": "postMessage", "Response": resp})

output_data = pd.DataFrame(messagesToSend)
output_data_2 = pd.DataFrame(responses)

omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.write_output_records(output_data_2, output_number=1)
omniscope_api.close()