from omniscope.api import OmniscopeApi
from visokio_omniprint import ImagesPdf, Image, Tools

import pandas as pd
import json, requests, os, re, tempfile
from urllib.parse import quote


# ---------------- Slack helpers ----------------

def slackify_links(text):
    if not text:
        return text
    url_pattern = r'(https?://[^\s]+(?: [^\s]+)*)'
    def repl(match):
        raw_url = match.group(0)
        encoded = quote(raw_url, safe=':/?=&%#.')
        return f"<{encoded}|{raw_url}>"
    return re.sub(url_pattern, repl, text)

def slack_upload_file_with_comment(channel_id, initial_comment, file_path, auth_token, display_name=None):

    if not os.path.isfile(file_path):
        raise Exception(f"Attachment file not found: {file_path}")

    filename = os.path.basename(file_path)
    title = display_name if display_name else filename
    length = os.path.getsize(file_path)

    headers_auth = {"Authorization": f"Bearer {auth_token}"}

    # 1) request upload slot
    r1 = requests.post(
        "https://slack.com/api/files.getUploadURLExternal",
        headers=headers_auth,
        files={
            "filename": (None, filename),
            "length": (None, str(length)),
        },
    )
    data1 = r1.json()
    if not data1.get("ok"):
        raise Exception(data1)

    upload_url = data1["upload_url"]
    file_id = data1["file_id"]

    # 2) upload bytes
    with open(file_path, "rb") as f:
        r2 = requests.post(upload_url, headers={"Content-Type": "application/octet-stream"}, data=f)
    if not r2.ok:
        raise Exception(r2.text)

    # 3) finalize post
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
    data3 = r3.json()
    if not data3.get("ok"):
        raise Exception(data3)

    return file_id


# ---------------- Main block ----------------

omniscope_api = OmniscopeApi()
input_data = omniscope_api.read_input_records(input_number=0)
input_data.fillna("", inplace=True)

# Screenshot options
url_field      = omniscope_api.get_option("url_field")
sleep_seconds  = omniscope_api.get_option("sleep_seconds")
resolution     = omniscope_api.get_option("resolution")
orientation    = omniscope_api.get_option("orientation")
create_pdf     = omniscope_api.get_option("create_pdf")
compressed     = omniscope_api.get_option("compression")

tinify         = omniscope_api.get_option("tinify")
tinify_key     = omniscope_api.get_option("tinify_key")
tinify_width   = omniscope_api.get_option("tinify_width")

auth_username  = omniscope_api.get_option("auth_username")
auth_password  = omniscope_api.get_option("auth_password")

# Slack options
channel_id     = omniscope_api.get_option("channelID")
authToken      = omniscope_api.get_option("authToken")
message_opt    = omniscope_api.get_option("message")

def as_bool(v):
    return str(v).lower() in ("1","true","yes","y","on")

tinify_bool = as_bool(tinify)
create_pdf_bool = as_bool(create_pdf)

is_docker = omniscope_api.is_docker()

tools = Tools()
image = Image()
images_pdf = ImagesPdf()

results = []
errors = []

# temp working folder (always deleted)
working_dir = tempfile.mkdtemp(prefix="omniscope_reports_")
generated_images = []

for idx, row in input_data.iterrows():
    try:
        # resolve URL
        url_val = row[url_field] if (url_field in input_data.columns) else url_field
        url = str(url_val).strip()

        if auth_username or auth_password:
            url = tools.add_basic_auth(url, auth_username, auth_password)

        # resolve message
        msg_val = row[message_opt] if (message_opt in input_data.columns) else message_opt
        message = str(msg_val).strip()

        # build comment without duplicating the link
        
        if message:
            if url in message:
                comment_text = message
            else:
                comment_text = message + "\n" + url
        else:
           comment_text = url

        comment = slackify_links(comment_text)

        # screenshot path
        image_path = os.path.join(working_dir, f"screenshot_{idx}.png")

        # take screenshot
        image.grab_screenshot_in_path(url, sleep_seconds, is_docker, image_path)

        # tinify
        if tinify_bool:
            image.tinify(tinify_key, image_path, tinify_width)

        generated_images.append(image_path)
        images_pdf.add_path(image_path)

        # post screenshot to Slack
        file_id = slack_upload_file_with_comment(
            channel_id,
            comment,
            image_path,
            authToken,
            "Omniscope Report"
        )

        results.append({"Row": idx, "Status": "posted", "SlackFileId": file_id})

    except Exception as e:
        errors.append({"Row": idx, "Error": str(e)})
        results.append({"Row": idx, "Status": "error"})


# ---------- Optional PDF ----------
if create_pdf_bool and generated_images:
    try:
        pdf_path = os.path.join(working_dir, "report.pdf")
        images_pdf.create_pdf_in_path(pdf_path, orientation, resolution, compressed)

        slack_upload_file_with_comment(
            channel_id,
            "Combined PDF snapshot",
            pdf_path,
            authToken,
            "Omniscope Report PDF"
        )
    except Exception as e:
        errors.append({"Row": "PDF", "Error": str(e)})


# ---------- Cleanup ----------
try:
    for f in os.listdir(working_dir):
        try:
            os.remove(os.path.join(working_dir, f))
        except:
            pass
    os.rmdir(working_dir)
except:
    pass


# ---------- Outputs ----------
out0 = pd.DataFrame(results)
if out0.shape[1] == 0:
    out0 = pd.DataFrame(columns=["Row","Status","SlackFileId"])

out1 = pd.DataFrame(errors)
if out1.shape[1] == 0:
    out1 = pd.DataFrame(columns=["Row","Error"])

omniscope_api.write_output_records(out0, output_number=0)
omniscope_api.write_output_records(out1, output_number=1)
omniscope_api.close()