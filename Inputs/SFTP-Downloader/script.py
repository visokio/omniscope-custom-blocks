"""SFTP Downloader: downloads the files in a folder on an SFTP server to a folder on the Omniscope server and lists
them, so an Append files block (or any block that takes file paths) can load them."""
import base64
import fnmatch
import hashlib
import os
import stat

import pandas as pd
import paramiko
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def option_text(name):
    value = omniscope_api.get_option(name)
    return str(value).strip() if value is not None else ""


hostname = option_text("hostname")
port = omniscope_api.get_option("port") or 22
username = option_text("username")
password = omniscope_api.get_option("password") or None
key_file = option_text("privateKeyFile")
host_key = option_text("hostKey")
folder = option_text("folder") or "."
extension = option_text("extension")
local_folder = option_text("localFolder")

if not hostname:
    omniscope_api.abort("Enter the SFTP server's host name.")
if not username:
    omniscope_api.abort("Enter the user name to sign in with.")
if not password and not key_file:
    omniscope_api.abort("Enter a password or choose a private key file.")
if key_file and not os.path.isfile(key_file):
    omniscope_api.abort(f"Private key file not found on the Omniscope server: {key_file}")

# Which files to take: patterns such as *.csv, or extensions such as csv / .csv, separated by commas.
patterns = []
for part in extension.split(","):
    part = part.strip()
    if part:
        patterns.append(part if any(c in part for c in "*?[") else "*." + part.lstrip("."))


def wanted(name):
    return not patterns or any(fnmatch.fnmatch(name.lower(), p.lower()) for p in patterns)


def fingerprint(key):
    """The SHA256 fingerprint as ssh-keygen -l prints it: SHA256:<base64 without padding>."""
    return "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")


class CheckHostKey(paramiko.MissingHostKeyPolicy):
    """Accept the server only if its key matches the Host key option (a SHA256 fingerprint or a known_hosts line)."""

    def missing_host_key(self, client, server, key):
        expected = host_key.split()
        offered = fingerprint(key)
        if expected and expected[0].startswith("SHA256:"):
            if expected[0].rstrip("=") == offered:
                return
        elif any(a == key.get_name() and b == key.get_base64() for a, b in zip(expected, expected[1:])):
            return  # a known_hosts or .pub line: "[host] key-type base64-key [comment]"
        raise paramiko.SSHException(f"The server's host key ({key.get_name()} {offered}) does not match the "
                                    f"Host key option. If the server's key has changed, check with its administrator "
                                    f"before updating the option.")


class AcceptAnyKey(paramiko.MissingHostKeyPolicy):
    def __init__(self):
        self.seen = None

    def missing_host_key(self, client, server, key):
        self.seen = f"{key.get_name()} {fingerprint(key)}"


# Empty: the block's own working folder on the Omniscope server, as in earlier versions of the block.
local_folder = local_folder or os.path.dirname(os.path.realpath(__file__))
os.makedirs(local_folder, exist_ok=True)

policy = CheckHostKey() if host_key else AcceptAnyKey()
client = paramiko.SSHClient()
client.set_missing_host_key_policy(policy)
rows = []
try:
    omniscope_api.update_message(f"Connecting to {hostname}:{port}")
    client.connect(hostname, port=int(port), username=username, password=password,
                   key_filename=key_file or None, look_for_keys=False, allow_agent=False, timeout=30)
    sftp = client.open_sftp()
    entries = sorted(sftp.listdir_attr(folder), key=lambda a: a.filename)
    for attr in entries:
        if attr.st_mode is not None and not stat.S_ISREG(attr.st_mode):
            continue  # folders, links and other non-files
        if not wanted(attr.filename):
            continue
        local_path = os.path.join(local_folder, attr.filename)
        omniscope_api.update_message(f"Downloading {attr.filename}")
        sftp.get(folder.rstrip("/") + "/" + attr.filename if folder != "." else attr.filename, local_path)
        rows.append({
            "File path": local_path,
            "File name": attr.filename,
            "Size (bytes)": attr.st_size,
            "Modified": pd.Timestamp(attr.st_mtime, unit="s") if attr.st_mtime is not None else pd.NaT,
        })
    sftp.close()
except paramiko.AuthenticationException:
    omniscope_api.abort(f"The SFTP server refused the sign-in for {username}. Check the user name, password or key.")
except (paramiko.SSHException, OSError) as error:
    omniscope_api.abort(f"SFTP failed ({hostname}:{port}, folder {folder}): {error}")
finally:
    client.close()

output = pd.DataFrame(rows, columns=["File path", "File name", "Size (bytes)", "Modified"])
output["Size (bytes)"] = output["Size (bytes)"].astype("Int64")
output["Modified"] = pd.to_datetime(output["Modified"])
omniscope_api.write_output_records(output, output_number=0)
message = f"Downloaded {len(output)} file(s) from {folder} to {local_folder}."
if not host_key and policy.seen:
    message += f" The server's key was not checked: to check it, set Host key to {policy.seen.split()[-1]}."
omniscope_api.commit(message)
