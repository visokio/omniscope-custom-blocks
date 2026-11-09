"""Tests for the GitHub block against a stand-in GitHub API. No test calls GitHub: requests.Session.request is
replaced by a fake that serves tests/canned/monthly-sales.csv, and for writing records every request that would be
sent, so the tests can check the commit the block would make."""

import base64
import io
import json
import json as _json
import os
import time
import zlib

import numpy as np
import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned", "monthly-sales.csv")
REPO = "octo-org/sales-data"
BASE = f"https://api.github.com/repos/{REPO}"
READ = {"repositoryPath": REPO, "filePath": "data/monthly-sales.csv"}
WRITE = {**READ, "mode": "WRITE", "githubToken": "github_pat_test"}


def response(status, body=None, raw=None):
    r = requests.Response()
    r.status_code = status
    r._content = raw if raw is not None else json.dumps(body or {}).encode("utf-8")
    r.url = BASE
    return r


class FakeGitHub:
    """A repository with branches main (default) and a-feature; serves one file; accepts commits."""

    def __init__(self, files=None, status=None):
        with open(CANNED, "rb") as fh:
            self.files = files if files is not None else {"data/monthly-sales.csv": fh.read()}
        self.status = status
        self.calls = []

    def __call__(self, session, method, url, params=None, json=None, headers=None, data=None, **kw):
        if json is None and data:  # a JSON body sent as text
            json = _json.loads(data)
        sent = dict(session.headers, **(headers or {}))
        self.calls.append({"method": method, "url": url, "params": params, "json": json, "headers": sent})
        if self.status:
            return response(self.status, {"message": "Bad credentials" if self.status == 401 else "Not Found"})
        url = url.replace("api.github.com:443", "api.github.com")
        path = url[len(BASE) :].split("?")[0] if url.startswith(BASE) else None
        if path is None:
            return response(404, {"message": "Not Found"})
        if method == "GET" and path == "":
            return response(200, {"full_name": REPO, "default_branch": "main"})
        if method == "GET" and path.startswith("/contents/"):
            name = requests.utils.unquote(path[len("/contents/") :])
            if name not in self.files:
                return response(404, {"message": "Not Found"})
            return response(200, raw=self.files[name])
        if method == "GET" and path.startswith("/git/ref/heads/"):
            branch = path[len("/git/ref/heads/") :]
            if branch not in ("main", "a-feature"):
                return response(404, {"message": "Not Found"})
            return response(
                200, {"ref": f"refs/heads/{branch}", "object": {"sha": f"head-of-{branch}", "type": "commit"}}
            )
        if method == "GET" and path.startswith("/git/commits/"):
            return response(200, {"sha": path.rsplit("/", 1)[1], "tree": {"sha": "tree-of-" + path.rsplit("/", 1)[1]}})
        # Endpoints the original version of the block used: every ref (listed alphabetically, as GitHub does),
        # the whole tree, and the file by its blob id
        if method == "GET" and path == "/git/refs":
            return response(
                200,
                [
                    {
                        "ref": f"refs/heads/{b}",
                        "url": f"{BASE}/git/refs/heads/{b}",
                        "object": {"sha": f"head-of-{b}", "type": "commit", "url": ""},
                    }
                    for b in ("a-feature", "main")
                ],
            )
        if method == "GET" and path.startswith("/git/trees/"):
            return response(
                200,
                {
                    "sha": "t",
                    "truncated": False,
                    "tree": [{"path": n, "mode": "100644", "type": "blob", "sha": "blob-" + n} for n in self.files],
                },
            )
        if method == "GET" and path.startswith("/git/blobs/"):
            name = path[len("/git/blobs/blob-") :]
            return response(
                200,
                {
                    "sha": "blob-" + name,
                    "encoding": "base64",
                    "content": base64.b64encode(self.files[requests.utils.unquote(name)]).decode(),
                },
            )
        if method == "POST" and path == "/git/blobs":
            return response(201, {"sha": "new-blob"})
        if method == "POST" and path == "/git/trees":
            return response(201, {"sha": "new-tree"})
        if method == "POST" and path == "/git/commits":
            return response(
                201, {"sha": "c0ffee1234567890", "html_url": f"https://github.com/{REPO}/commit/c0ffee1234567890"}
            )
        if method in ("PATCH", "POST") and path.startswith("/git/refs/heads/"):
            return response(200, {"object": {"sha": json["sha"]}})
        return response(404, {"message": "Not Found"})

    def find(self, method, ending):
        return [c for c in self.calls if c["method"] == method and c["url"].endswith(ending)]


def install(monkeypatch, fake):
    monkeypatch.setattr(requests.Session, "request", lambda session, *a, **kw: fake(session, *a, **kw))
    return fake


@pytest.fixture
def github(monkeypatch):
    return install(monkeypatch, FakeGitHub())


def written_csv(fake):
    blob = fake.find("POST", "/git/blobs")[0]["json"]
    assert blob["encoding"] == "base64"
    return base64.b64decode(blob["content"])


# ---------------------------------------------------------------- reading


def test_read_a_public_file(github):
    res = run_block(HERE, None, READ).raise_for_error()
    data = res.output(0)
    assert len(data) == 36 and data.columns.tolist() == ["Month", "Region", "Orders", "Revenue"]
    assert data["Orders"].sum() == 8829 and data["Revenue"].iloc[0] == 18279.90
    call = github.calls[0]
    assert call["url"] == f"{BASE}/contents/data/monthly-sales.csv" and call["params"] is None
    assert call["headers"]["Accept"] == "application/vnd.github.raw+json"
    assert "Authorization" not in call["headers"]  # no token, no header
    assert len(github.calls) == 1
    assert res.final_message == "Read 36 records from data/monthly-sales.csv."


def test_read_from_a_branch_with_a_token_and_a_pasted_address(github):
    run_block(
        HERE,
        None,
        {
            **READ,
            "repositoryPath": "https://github.com/octo-org/sales-data.git",
            "branch": "a-feature",
            "githubToken": "github_pat_test",
        },
    ).raise_for_error()
    call = github.calls[0]
    assert call["url"].startswith(BASE) and call["params"] == {"ref": "a-feature"}
    assert call["headers"]["Authorization"] == "Bearer github_pat_test"


def test_read_compressed_and_other_separators(monkeypatch):
    with open(CANNED, "rb") as fh:
        plain = fh.read()
    fake = install(monkeypatch, FakeGitHub({"a.csv.z": zlib.compress(plain), "b.tsv": plain.replace(b",", b"\t")}))
    out = run_block(HERE, None, {**READ, "filePath": "a.csv.z", "compressed": True}).raise_for_error().output(0)
    assert len(out) == 36
    out = run_block(HERE, None, {**READ, "filePath": "b.tsv", "separator": "\\t"}).raise_for_error().output(0)
    assert out.columns.tolist() == ["Month", "Region", "Orders", "Revenue"]
    res = run_block(HERE, None, {**READ, "filePath": "b.tsv", "compressed": True})
    assert res.status == "aborted" and "not zlib-compressed" in res.final_message
    assert len(fake.calls) == 3


def test_text_that_is_not_a_table_becomes_one_record(monkeypatch):
    # The original's fallback, pd.DataFrame(data={"content": text}), raised "you must pass an index"
    install(monkeypatch, FakeGitHub({"notes.md": b"", "odd.txt": b'a,b\n"unclosed,1\n'}))
    out = run_block(HERE, None, {**READ, "filePath": "notes.md"}).raise_for_error().output(0)
    assert out.columns.tolist() == ["content"] and out["content"].tolist() == [""]
    out = run_block(HERE, None, {**READ, "filePath": "odd.txt"}).raise_for_error().output(0)
    assert out["content"].tolist() == ['a,b\n"unclosed,1\n']


def test_missing_file_private_repository_and_bad_token(monkeypatch):
    # The original called cancel() and carried on, so the error shown was a later Python error
    install(monkeypatch, FakeGitHub())
    res = run_block(HERE, None, {**READ, "filePath": "data/nope.csv"})
    assert res.status == "aborted" and "found no file data/nope.csv" in res.final_message
    assert "needs an access token" in res.final_message
    install(monkeypatch, FakeGitHub(status=401))
    res = run_block(HERE, None, {**READ, "githubToken": "wrong"})
    assert res.status == "aborted" and "refused" in res.final_message and "Bad credentials" in res.final_message
    res = run_block(HERE, None, {**READ, "repositoryPath": "just-a-name"})
    assert res.status == "aborted" and "owner/repository" in res.final_message
    res = run_block(HERE, None, {**READ, "filePath": " "})
    assert res.status == "aborted" and "file path" in res.final_message


# ---------------------------------------------------------------- writing


def sales_frame():
    return pd.read_csv(CANNED)


def test_write_makes_one_commit_on_the_default_branch(github):
    res = run_block(HERE, sales_frame(), WRITE).raise_for_error()
    methods = [(c["method"], c["url"][len(BASE) :]) for c in github.calls]
    assert methods == [
        ("GET", ""),  # the default branch
        ("GET", "/git/ref/heads/main"),  # its last commit
        ("GET", "/git/commits/head-of-main"),  # that commit's tree
        ("POST", "/git/blobs"),  # the file
        ("POST", "/git/trees"),  # the tree with the file replaced
        ("POST", "/git/commits"),  # the commit
        ("PATCH", "/git/refs/heads/main"),  # the branch moved to it
    ]
    tree = github.find("POST", "/git/trees")[0]["json"]
    assert tree == {
        "base_tree": "tree-of-head-of-main",
        "tree": [{"path": "data/monthly-sales.csv", "mode": "100644", "type": "blob", "sha": "new-blob"}],
    }
    commit = github.find("POST", "/git/commits")[0]["json"]
    assert commit == {
        "message": "Update data/monthly-sales.csv from Omniscope",
        "tree": "new-tree",
        "parents": ["head-of-main"],
    }
    assert github.find("PATCH", "/git/refs/heads/main")[0]["json"] == {"sha": "c0ffee1234567890", "force": False}
    assert all(c["headers"]["Authorization"] == "Bearer github_pat_test" for c in github.calls)
    written = pd.read_csv(io.BytesIO(written_csv(github)))
    assert written.shape == (36, 4) and written["Orders"].sum() == 8829
    result = res.output(0)
    assert result.iloc[0].to_dict() == {
        "Repository": REPO,
        "Branch": "main",
        "File path": "data/monthly-sales.csv",
        "Records written": 36,
        "Bytes": len(written_csv(github)),
        "Commit": "c0ffee1234567890",
        "Commit URL": "https://github.com/octo-org/sales-data/commit/c0ffee1234567890",
    }


def test_write_to_a_named_branch_with_a_message_compressed(github):
    # The original always moved the first ref GitHub listed (alphabetical: "a-feature" before "main"), not main
    run_block(
        HERE,
        sales_frame(),
        {**WRITE, "branch": "a-feature", "commitMessage": "June figures", "compressed": True, "separator": ";"},
    ).raise_for_error()
    assert [c for c in github.calls if c["url"] == BASE] == []  # no need to look up the default branch
    assert github.find("PATCH", "/git/refs/heads/a-feature") and not github.find("PATCH", "/git/refs/heads/main")
    assert github.find("POST", "/git/commits")[0]["json"]["message"] == "June figures"
    text = zlib.decompress(written_csv(github)).decode("utf-8")
    assert text.splitlines()[0] == "Month;Region;Orders;Revenue"


def test_write_needs_input_and_token(github):
    res = run_block(HERE, None, WRITE)
    assert res.status == "aborted" and "Connect the records" in res.final_message
    res = run_block(HERE, sales_frame(), {**WRITE, "githubToken": None})
    assert res.status == "aborted" and "access token" in res.final_message
    res = run_block(HERE, sales_frame(), {**WRITE, "branch": "no-such-branch"})
    assert res.status == "aborted" and "found no branch no-such-branch" in res.final_message
    assert github.find("POST", "/git/blobs") == []  # nothing written


def test_write_refused_when_the_branch_moved(monkeypatch):
    class Moved(FakeGitHub):
        def __call__(self, session, method, url, **kw):
            if method == "PATCH":
                self.calls.append({"method": method, "url": url, "params": None, "json": kw.get("json"), "headers": {}})
                return response(422, {"message": "Update is not a fast forward"})
            return super().__call__(session, method, url, **kw)

    install(monkeypatch, Moved())
    res = run_block(HERE, sales_frame(), WRITE)
    assert res.status == "aborted" and "Update is not a fast forward" in res.final_message


def test_write_empty_input_writes_the_header(github):
    empty = sales_frame().iloc[0:0]
    res = run_block(HERE, empty, WRITE).raise_for_error()
    assert written_csv(github).decode("utf-8").strip() == "Month,Region,Orders,Revenue"
    assert res.output(0)["Records written"].item() == 0


def test_write_large_input(github):
    rng = np.random.default_rng(1)
    n = 200_000
    df = pd.DataFrame({"id": np.arange(n), "region": rng.choice(["North", "South"], n), "value": rng.normal(size=n)})
    t0 = time.time()
    res = run_block(HERE, df, WRITE).raise_for_error()
    assert res.output(0)["Records written"].item() == n
    assert len(pd.read_csv(io.BytesIO(written_csv(github)))) == n
    assert time.time() - t0 < 60


def test_placeholder_matches_the_read_output(github):
    data = run_block(HERE, None, READ).raise_for_error().output(0)
    placeholder = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"))
    pd.testing.assert_frame_equal(placeholder, data, check_dtype=False)


def test_manifest_dependencies_match_the_scripts_third_party_imports():
    """Omniscope pip-installs the manifest's `dependencies` on first run: it must name what script.py imports
    (requests), not an unused package (it said PyGithub, so a server without requests failed on import)."""
    import ast
    with open(os.path.join(HERE, "manifest.json"), encoding="utf-8") as fh:
        deps = {d.strip() for d in json.load(fh).get("dependencies", "").split(",") if d.strip()}
    with open(os.path.join(HERE, "script.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert "requests" in imported
    assert deps == {"requests"}
