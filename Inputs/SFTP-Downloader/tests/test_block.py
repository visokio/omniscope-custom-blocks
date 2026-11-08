"""Tests for the SFTP Downloader block. No connection is made: paramiko.SSHClient is replaced by a fake that serves
the canned folder tests/canned/server/ and offers the canned host key tests/canned/host_key.pub."""
import base64
import hashlib
import os
import shutil
import stat
import time

import pandas as pd
import paramiko
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
CANNED = os.path.join(HERE, "tests", "canned")
SERVER = os.path.join(CANNED, "server")
with open(os.path.join(CANNED, "host_key.pub"), encoding="utf-8") as fh:
    HOST_KEY_LINE = fh.read().strip()
HOST_KEY = paramiko.Ed25519Key(data=base64.b64decode(HOST_KEY_LINE.split()[1]))
FINGERPRINT = "SHA256:" + base64.b64encode(hashlib.sha256(HOST_KEY.asbytes()).digest()).decode().rstrip("=")
# Modification times on the fake server (git does not keep file times)
MTIMES = {"daily-sales-2025-03-03.csv": "2025-03-03 02:00", "daily-sales-2025-03-04.csv": "2025-03-04 02:00",
          "daily-sales-2025-03-05.csv": "2025-03-05 02:00", "stores.CSV": "2025-01-10 09:30", "README.txt": "2025-01-10 09:30"}


class FakeSFTP:
    def __init__(self, server):
        self.server = server
        self.gets = []

    def _local(self, path):
        return os.path.join(SERVER, path.lstrip("/"))

    def listdir_attr(self, path="."):
        folder = self._local(path)
        if not os.path.isdir(folder):
            raise FileNotFoundError(2, "No such file")
        out = []
        for name in os.listdir(folder):
            attr = paramiko.SFTPAttributes.from_stat(os.stat(os.path.join(folder, name)), name)
            if name in MTIMES:
                attr.st_mtime = int(pd.Timestamp(MTIMES[name]).timestamp())
            out.append(attr)
        return out

    def get(self, remotepath, localpath):
        self.gets.append(remotepath)
        shutil.copyfile(self._local(remotepath), localpath)

    def close(self):
        pass


class FakeSSH:
    """Stands in for paramiko.SSHClient; records how it was used."""
    instances = []
    password = "s3cret"

    def __init__(self):
        self.policy = None
        self.connected = None
        self.sftp = FakeSFTP(SERVER)
        self.closed = False
        FakeSSH.instances.append(self)

    def set_missing_host_key_policy(self, policy):
        self.policy = policy

    def connect(self, hostname, port=22, username=None, password=None, key_filename=None, **kw):
        self.connected = dict(hostname=hostname, port=port, username=username, password=password,
                              key_filename=key_filename, **kw)
        if hostname == "unreachable.example.com":
            raise OSError("[Errno 111] Connection refused")
        self.policy.missing_host_key(self, hostname, HOST_KEY)  # as paramiko does for an unknown server
        if key_filename is None and password != FakeSSH.password:
            raise paramiko.AuthenticationException("Authentication failed.")

    def open_sftp(self):
        return self.sftp

    def close(self):
        self.closed = True


@pytest.fixture
def ssh(monkeypatch):
    FakeSSH.instances = []
    monkeypatch.setattr(paramiko, "SSHClient", FakeSSH)
    return FakeSSH


def download(tmp_path, **options):
    base = {"hostname": "sftp.example.com", "username": "reports", "password": "s3cret", "folder": "/outgoing",
            "extension": "csv", "localFolder": str(tmp_path / "downloads")}
    return run_block(HERE, None, {**base, **options})


def test_downloads_matching_files_and_lists_them(ssh, tmp_path):
    res = download(tmp_path).raise_for_error()
    out = res.output(0)
    # files only (not the archive folder), extension not case-sensitive, sorted by name
    assert out["File name"].tolist() == ["daily-sales-2025-03-03.csv", "daily-sales-2025-03-04.csv",
                                         "daily-sales-2025-03-05.csv", "stores.CSV"]
    assert out["File path"].tolist() == [str(tmp_path / "downloads" / n) for n in out["File name"]]
    assert (tmp_path / "downloads" / "stores.CSV").read_text().startswith("Store,Region,Manager")
    assert out["Size (bytes)"].tolist() == [182, 182, 182, 100]
    assert out["Modified"].iloc[0] == pd.Timestamp("2025-03-03 02:00")
    assert ssh.instances[0].sftp.gets[0] == "/outgoing/daily-sales-2025-03-03.csv"
    c = ssh.instances[0].connected
    assert (c["hostname"], c["port"], c["username"], c["look_for_keys"]) == ("sftp.example.com", 22, "reports", False)
    assert ssh.instances[0].closed
    assert FINGERPRINT in res.final_message  # not checked, so the message offers the fingerprint


def test_patterns_and_all_files(ssh, tmp_path):
    out = download(tmp_path, extension="daily-*.csv, .txt").raise_for_error().output(0)
    assert out["File name"].tolist() == ["README.txt", "daily-sales-2025-03-03.csv", "daily-sales-2025-03-04.csv",
                                         "daily-sales-2025-03-05.csv"]
    out = download(tmp_path, extension=None).raise_for_error().output(0)
    assert len(out) == 5  # every file, but not the sub-folder


def test_sub_folders_are_skipped(ssh, tmp_path):
    # The original block called get() on the archive folder too, and failed
    out = download(tmp_path, extension="").raise_for_error().output(0)
    assert "archive" not in out["File name"].tolist()


def test_host_key_checked_when_given(ssh, tmp_path):
    assert download(tmp_path, hostKey=FINGERPRINT).raise_for_error().output(0).shape[0] == 4
    assert download(tmp_path, hostKey=HOST_KEY_LINE).raise_for_error().output(0).shape[0] == 4
    res = download(tmp_path, hostKey="SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    assert res.status == "aborted" and "does not match" in res.final_message and FINGERPRINT in res.final_message
    assert ssh.instances[-1].sftp.gets == []


def test_sign_in_failures_and_unreachable_servers(ssh, tmp_path):
    res = download(tmp_path, password="wrong")
    assert res.status == "aborted" and "refused the sign-in for reports" in res.final_message
    res = download(tmp_path, hostname="unreachable.example.com")
    assert res.status == "aborted" and "Connection refused" in res.final_message
    res = download(tmp_path, folder="/missing")
    assert res.status == "aborted" and "folder /missing" in res.final_message


def test_private_key_file(ssh, tmp_path):
    key = tmp_path / "id_ed25519"
    key.write_text("not read by the fake")
    download(tmp_path, password=None, privateKeyFile=str(key)).raise_for_error()
    assert ssh.instances[0].connected["key_filename"] == str(key)
    res = download(tmp_path, password=None, privateKeyFile=str(tmp_path / "nope"))
    assert res.status == "aborted" and "Private key file not found" in res.final_message


def test_option_checks(ssh, tmp_path):
    assert "host name" in download(tmp_path, hostname=" ").final_message
    assert "user name" in download(tmp_path, username=None).final_message
    assert "password or choose a private key" in download(tmp_path, password=None).final_message
    assert ssh.instances == []


def test_empty_folder_gives_no_records_with_fields(ssh, tmp_path):
    out = download(tmp_path, extension="parquet").raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["File path", "File name", "Size (bytes)", "Modified"]


def test_default_download_folder_is_the_blocks_working_folder(ssh, tmp_path):
    res = download(tmp_path, localFolder=None, extension="stores.*").raise_for_error()
    path = res.output(0)["File path"].iloc[0]
    try:
        assert os.path.dirname(path) == os.path.realpath(HERE)
    finally:
        os.remove(path)


def test_many_files(ssh, tmp_path, monkeypatch):
    big = tmp_path / "server" / "outgoing"
    big.mkdir(parents=True)
    for k in range(3000):
        (big / f"part-{k:04d}.csv").write_text("a,b\n1,2\n")
    monkeypatch.setattr(FakeSFTP, "_local", lambda self, path: os.path.join(tmp_path / "server", path.lstrip("/")))
    t0 = time.time()
    out = download(tmp_path).raise_for_error().output(0)
    assert time.time() - t0 < 60 and len(out) == 3000
