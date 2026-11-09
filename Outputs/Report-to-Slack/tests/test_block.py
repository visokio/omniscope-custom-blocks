"""Tests for Send Report to Slack. Neither Chrome nor Slack is used: the visokio_omniprint package is replaced by a
stand-in that writes a PNG the size of the page area Chrome would show, and requests.post by a stand-in that
records each request and answers with the canned Slack responses in tests/canned/."""
import json
import os
import struct
import sys
import time
import types
import zlib
from urllib.parse import quote, urlparse

import pandas as pd
import pytest
import requests

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "report-links.csv")
CANNED = os.path.join(HERE, "tests", "canned")
TOKEN = "xoxb-test-token"
SETTINGS = {"url_field": "Report URL", "message": "Message", "authToken": TOKEN, "channelID": "C0123ABCD"}
SALES = "http://127.0.0.1:24679/Sales/Monthly%20Review.iox/r/Board%20Pack/#Overview"

# ---------------------------------------------------------------- stand-in for visokio_omniprint (no Chrome)


def png(width, height):
    """A valid one-colour PNG of the given size."""
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + b"\x30\x80\x60" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def png_size(path):
    with open(path, "rb") as fh:
        return struct.unpack(">II", fh.read(24)[16:24])


class FakeChrome:
    """Records what the block asks of Chrome. Like headless Chrome, the window opens at 1920x1080 and the page area
    is 143 pixels shorter than the window; a screenshot is the page area."""

    BAR = 143

    def __init__(self, fail_on=None):
        self.visits, self.tinified, self.pdfs, self.fail_on = [], [], [], fail_on

    def module(self):
        chrome = self

        class Driver:
            def __init__(self):
                self.size = (1920, 1080)

            def set_window_size(self, w, h):
                self.size = (w, h)

            def execute_script(self, script):
                assert "outerHeight - window.innerHeight" in script
                return [0, chrome.BAR]

        class DriverBase:
            def get_driver(self, is_docker):
                return Driver()

            def get_driver_for_url(self, url, timeout, is_docker):
                driver = self.get_driver(is_docker)
                if chrome.fail_on and chrome.fail_on in url:
                    raise Exception(f"Message: unknown error: net::ERR_NAME_NOT_RESOLVED ({url})")
                chrome.visits.append({"url": url, "timeout": timeout, "is_docker": is_docker})
                return driver

        class Image(DriverBase):
            def grab_screenshot_in_path(self, url, timeout, is_docker, path):
                driver = self.get_driver_for_url(url, timeout, is_docker)
                w, h = driver.size
                with open(path, "wb") as fh:
                    fh.write(png(w, h - chrome.BAR))

            def tinify(self, key, path, width):
                w, h = png_size(path)
                chrome.tinified.append({"key": key, "path": path, "width": width})
                with open(path, "wb") as fh:
                    fh.write(png(width, round(h * width / w)))

        class ImagesPdf(DriverBase):
            def __init__(self):
                self.paths = []

            def add_path(self, path):
                self.paths.append(path)

            def create_pdf_in_path(self, path, orientation, resolution, compressed):
                chrome.pdfs.append({"path": path, "orientation": orientation, "resolution": resolution,
                                    "compressed": compressed, "pages": [png_size(p) for p in self.paths]})
                with open(path, "wb") as fh:
                    fh.write(b"%PDF-1.3\n% stand-in\n")

        class ImagesPPTX(ImagesPdf):
            def create_pptx_in_path(self, path, orientation, resolution):
                from pptx import Presentation
                from pptx.util import Inches
                prs = Presentation()
                for p in self.paths:
                    prs.slides.add_slide(prs.slide_layouts[6]).shapes.add_picture(p, 0, 0, Inches(10))
                prs.save(path)

        class Tools:
            def add_basic_auth(self, url, user, password):  # as visokio-omniprint 1.3.4 does it
                if not user or not user.strip() or not password or not password.strip():
                    return url
                p = urlparse(url)
                return f"{p.scheme}://{quote(user)}:{quote(password)}@{p.netloc}{p.path}"

        mod = types.ModuleType("visokio_omniprint")
        mod.Image, mod.ImagesPdf, mod.ImagesPPTX, mod.Tools = Image, ImagesPdf, ImagesPPTX, Tools
        return mod


@pytest.fixture
def chrome(monkeypatch):
    fake = FakeChrome()
    monkeypatch.setitem(sys.modules, "visokio_omniprint", fake.module())
    return fake


def canned(name):
    with open(os.path.join(CANNED, name + ".json"), encoding="utf-8") as fh:
        return fh.read().encode("utf-8")


def response(status, body):
    r = requests.Response()
    r.status_code = status
    r._content = body
    return r


class FakeSlack:
    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    def __call__(self, url, data=None, headers=None, files=None, timeout=None, **kw):
        if hasattr(data, "read"):
            data = data.read()
        self.calls.append({"url": url, "data": data, "headers": headers or {}, "files": files, "timeout": timeout})
        if url.startswith("https://files.slack.com/upload/"):
            return response(200, b"OK - " + str(len(data)).encode())
        if self.fail:
            return response(200, canned("error." + self.fail))
        return response(200, canned(url.rsplit("/", 1)[-1]))

    def uploads(self):
        """(file name, bytes, comment) for each completed upload."""
        names = [c["files"]["filename"][1] for c in self.calls if c["url"].endswith("getUploadURLExternal")]
        blobs = [c["data"] for c in self.calls if c["url"].startswith("https://files.slack.com/")]
        comments = [c["files"]["initial_comment"][1] for c in self.calls if c["url"].endswith("completeUploadExternal")]
        return list(zip(names, blobs, comments))


@pytest.fixture
def slack(monkeypatch):
    fake = FakeSlack()
    monkeypatch.setattr(requests, "post", fake)
    return fake


def blob_size(blob):
    return struct.unpack(">II", blob[16:24])


def test_sample_posts_a_screenshot_per_record_and_the_pdf(chrome, slack):
    res = run_block(HERE, SAMPLE, SETTINGS).raise_for_error()
    uploads = slack.uploads()
    assert [u[0] for u in uploads] == ["screenshot_0.png", "screenshot_1.png", "screenshot_2.png", "report.pdf"]
    assert [blob_size(u[1]) for u in uploads[:3]] == [(1280, 720)] * 3  # the original: 1920x937
    assert uploads[0][2] == f"Monthly sales review: revenue 4% above target.\n<{SALES}|{SALES}>"
    assert uploads[3][2] == "Combined PDF snapshot"
    assert chrome.pdfs[0]["pages"] == [(1280, 720)] * 3
    assert all(c["headers"].get("Authorization") == "Bearer " + TOKEN for c in slack.calls
               if c["url"].startswith("https://slack.com/"))
    out = res.output(0)
    assert out.columns.tolist() == ["Row", "Status", "SlackFileId"]
    assert out["Status"].tolist() == ["posted"] * 3 and out["SlackFileId"].tolist() == ["F0123FILE1"] * 3
    assert len(res.output(1)) == 0 and res.output(1).columns.tolist() == ["Row", "Error"]
    assert res.final_message == "3 screenshots posted to C0123ABCD."


def test_a_link_already_in_the_message_is_not_repeated(chrome, slack):
    run_block(HERE, SAMPLE, SETTINGS).raise_for_error()
    cash = "http://127.0.0.1:24679/Finance/Quarterly%20Review.iox/r/Quarterly%20Review/#Cash"
    assert slack.uploads()[2][2] == f"Cash position at month end (full report: <{cash}|{cash}>)."


def test_the_password_opens_the_page_but_never_reaches_slack(chrome, slack):
    # The original added user:password@ to the address and then posted that address in the Slack message, and
    # lost the #tab, so the screenshot showed the Report's first tab
    res = run_block(HERE, SAMPLE, {**SETTINGS, "auth_username": "bot", "auth_password": "Secret1"})
    res.raise_for_error()
    assert chrome.visits[0]["url"] == ("http://bot:Secret1@127.0.0.1:24679/Sales/Monthly%20Review.iox/r/Board%20Pack"
                                       "/#Overview")
    assert not any("Secret1" in u[2] for u in slack.uploads())
    assert slack.uploads()[0][2].endswith(f"<{SALES}|{SALES}>")


def test_integer_fields_with_missing_values_and_an_empty_message(chrome, slack):
    # The original's fillna('') failed on an Int64 field with a missing value
    df = pd.DataFrame({"Report URL": [SALES, SALES], "Message": ["Sales < plan & falling", None], "n": [1, None]})
    run_block(HERE, df, {**SETTINGS, "create_pdf": False}).raise_for_error()
    assert [u[2] for u in slack.uploads()] == [f"Sales &lt; plan &amp; falling\n<{SALES}|{SALES}>",
                                               f"<{SALES}|{SALES}>"]


def test_one_failed_screenshot_is_reported_and_the_rest_are_posted(monkeypatch, slack):
    fake = FakeChrome(fail_on="Stock.iox")
    monkeypatch.setitem(sys.modules, "visokio_omniprint", fake.module())
    res = run_block(HERE, SAMPLE, {**SETTINGS, "auth_username": "bot", "auth_password": "Secret1"})
    res.raise_for_error()
    assert res.output(0)["Status"].tolist() == ["posted", "error", "posted"]
    errors = res.output(1)
    assert errors["Row"].tolist() == ["1"] and "ERR_NAME_NOT_RESOLVED" in errors["Error"][0]
    assert "Secret1" not in errors["Error"][0]
    assert res.final_message == "2 screenshots posted to C0123ABCD; 1 error (see the Errors output)."


def test_nothing_posted_stops_the_block(chrome, monkeypatch):
    # The original finished as if all was well, with every record marked "error"
    monkeypatch.setattr(requests, "post", FakeSlack(fail="not_in_channel"))
    res = run_block(HERE, SAMPLE, SETTINGS)
    assert res.status == "aborted" and "not_in_channel (add the app" in res.final_message


def test_missing_settings_stop_before_any_screenshot(chrome, slack):
    for missing, words in (("authToken", "token"), ("channelID", "channel"), ("url_field", "Report URLs")):
        res = run_block(HERE, SAMPLE, {**SETTINGS, missing: None})
        assert res.status == "aborted" and words in res.final_message
    res = run_block(HERE, SAMPLE, {**SETTINGS, "tinify": True})
    assert res.status == "aborted" and "Tinify needs" in res.final_message
    assert run_block(HERE, None, SETTINGS).status == "aborted"
    assert chrome.visits == [] and slack.calls == []


def test_portrait_size_tinify_and_no_pdf(chrome, slack):
    res = run_block(HERE, SAMPLE, {**SETTINGS, "resolution": "1024x768", "orientation": "P", "create_pdf": False,
                                   "tinify": True, "tinify_key": "tk", "tinify_width": 384}).raise_for_error()
    assert [blob_size(u[1]) for u in slack.uploads()] == [(384, 512)] * 3
    assert chrome.pdfs == [] and len(res.output(0)) == 3


def test_empty_input_and_empty_urls(chrome, slack):
    df = pd.DataFrame({"Report URL": pd.Series([], dtype=object), "Message": pd.Series([], dtype=object)})
    res = run_block(HERE, df, SETTINGS).raise_for_error()
    assert slack.calls == [] and len(res.output(0)) == 0
    df = pd.DataFrame({"Report URL": [None, SALES], "Message": ["a", "b"]})
    res = run_block(HERE, df, SETTINGS).raise_for_error()
    assert res.output(0)["Status"].tolist() == ["skipped", "posted"]


def test_many_records(chrome, slack):
    n = 300
    df = pd.DataFrame({"Report URL": [f"{SALES}{i}" for i in range(n)], "Message": [f"Tab {i}" for i in range(n)]})
    t0 = time.time()
    res = run_block(HERE, df, {**SETTINGS, "resolution": "1024x768"}).raise_for_error()
    assert time.time() - t0 < 60
    assert len(slack.uploads()) == n + 1 and (res.output(0)["Status"] == "posted").all()
