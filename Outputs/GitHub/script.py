"""GitHub: reads a delimited file from a GitHub repository into records, or writes the input records to a file
in a repository as a new commit, through GitHub's REST API."""
import base64
import io
import re
import zlib
from urllib.parse import quote

import pandas as pd
import requests
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

API = "https://api.github.com"
TIMEOUT = 120


def option_text(name):
    value = omniscope_api.get_option(name)
    return "" if value is None else str(value).strip()


def repository(text):
    """owner/name, also from a pasted address such as https://github.com/owner/name.git"""
    text = re.sub(r"^(https?://)?(www\.)?github\.com/", "", text.strip(), flags=re.I)
    text = re.sub(r"\.git$", "", text.strip("/"))
    parts = text.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        omniscope_api.abort("Repository path must be owner/repository, such as octo-org/sales-data.")
    return f"{parts[0]}/{parts[1]}"


def separator_value(text):
    """The field separator: "," when empty; "\\t" or "tab" for a tab."""
    if not text:
        return ","
    if text.strip().lower() in ("\\t", "tab"):
        return "\t"
    return text


class GitHub:
    def __init__(self, repo, token):
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.has_token = bool(token)

    def call(self, method, path, what, **kw):
        response = self.session.request(method, f"{API}/repos/{self.repo}{path}", timeout=TIMEOUT, **kw)
        if response.ok:
            return response
        status = response.status_code
        try:
            detail = response.json().get("message", "")
        except ValueError:
            detail = response.text[:200]
        if status == 404:
            hint = "" if self.has_token else " A private repository needs an access token."
            omniscope_api.abort(f"GitHub found no {what} ({self.repo}).{hint}")
        if status in (401, 403):
            omniscope_api.abort(f"GitHub refused access to {what} ({status}: {detail}). Check the access token and "
                                "that it can read (or, to write, change the contents of) this repository.")
        if status == 409 or status == 422:
            omniscope_api.abort(f"GitHub could not update {what} ({status}: {detail}).")
        omniscope_api.abort(f"GitHub returned {status} for {what}: {detail}")

    def default_branch(self):
        return self.call("GET", "", "repository").json()["default_branch"]

    def read_file(self, path, branch):
        params = {"ref": branch} if branch else None
        response = self.call("GET", f"/contents/{quote(path)}", f"file {path}", params=params,
                             headers={"Accept": "application/vnd.github.raw+json"})
        return response.content

    def write_file(self, path, branch, content, message):
        """One commit on the branch that replaces (or adds) the file; the rest of the tree is kept."""
        ref = quote(branch)
        head = self.call("GET", f"/git/ref/heads/{ref}", f"branch {branch}").json()["object"]["sha"]
        base_tree = self.call("GET", f"/git/commits/{head}", "the branch's last commit").json()["tree"]["sha"]
        blob = self.call("POST", "/git/blobs", "the file contents", json={
            "content": base64.b64encode(content).decode("ascii"), "encoding": "base64"}).json()["sha"]
        entry = {"path": path, "mode": "100644", "type": "blob", "sha": blob}
        tree = self.call("POST", "/git/trees", "the file tree",
                         json={"base_tree": base_tree, "tree": [entry]}).json()["sha"]
        commit = self.call("POST", "/git/commits", "the commit", json={
            "message": message, "tree": tree, "parents": [head]}).json()
        self.call("PATCH", f"/git/refs/heads/{ref}", f"branch {branch}", json={"sha": commit["sha"], "force": False})
        return commit


repo_path = repository(option_text("repositoryPath"))
file_path = option_text("filePath").strip("/")
token = option_text("githubToken")
mode = option_text("mode") or "READ"
compressed = bool(omniscope_api.get_option("compressed"))
separator = separator_value(omniscope_api.get_option("separator") or "")
branch = option_text("branch")

if not file_path:
    omniscope_api.abort("Enter the file path within the repository, such as data/sales.csv.")

github = GitHub(repo_path, token)

if mode == "READ":
    content = github.read_file(file_path, branch)
    if compressed:
        try:
            content = zlib.decompress(content)
        except zlib.error as exc:
            omniscope_api.abort(f"The file is not zlib-compressed ({exc}); untick Compressed.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        omniscope_api.abort("The file is not UTF-8 text. Is it compressed? Then tick Compressed.")
    try:
        data = pd.read_csv(io.StringIO(text), sep=separator)
    except (pd.errors.ParserError, pd.errors.EmptyDataError):
        # Not delimited text (or empty): the whole file as one record
        data = pd.DataFrame({"content": [text]})
    omniscope_api.write_output_records(data, output_number=0)
    omniscope_api.close(f"Read {len(data):,} records from {file_path}.")

elif mode == "WRITE":
    data = omniscope_api.read_input_records(input_number=0)
    if data is None:
        omniscope_api.abort("Connect the records to write to the block's input.")
    if not token:
        omniscope_api.abort("Writing needs an access token that can change the repository's contents.")
    content = data.to_csv(sep=separator, index=False).encode("utf-8")
    if compressed:
        content = zlib.compress(content)
    target = branch or github.default_branch()
    message = option_text("commitMessage") or f"Update {file_path} from Omniscope"
    commit = github.write_file(file_path, target, content, message)
    result = pd.DataFrame({
        "Repository": [repo_path], "Branch": [target], "File path": [file_path], "Records written": [len(data)],
        "Bytes": [len(content)], "Commit": [commit["sha"]],
        "Commit URL": [commit.get("html_url") or f"https://github.com/{repo_path}/commit/{commit['sha']}"],
    })
    omniscope_api.write_output_records(result, output_number=0)
    omniscope_api.close(f"Wrote {len(data):,} records to {file_path} on {target} (commit {commit['sha'][:7]}).")

else:
    omniscope_api.abort(f"Unknown mode {mode!r}: choose Read or Write.")
