"""Tests for Web Image-PDF output. Chrome is not started: the visokio_omniprint package is replaced by a stand-in
that records each page visited and writes a PNG the size of the page area Chrome would show, so the tests check
the addresses, the screenshot sizes, the file names and the PDF requested."""
import os
import struct
import sys
import time
import types
import zlib
from urllib.parse import quote, urlparse

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "web-pages.csv")
TAB = "http://127.0.0.1:24679/Sales/Monthly%20Review.iox/r/Board%20Pack/#Overview"

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


def options(folder, **kw):
    return {"url_field": "URL", "folder_path": str(folder), **kw}


def test_sample_screenshots_are_the_chosen_size(chrome, tmp_path):
    # The original always shot Chrome's default window (1920x1080, a 1920x937 page area) whatever the resolution
    res = run_block(HERE, SAMPLE, options(tmp_path)).raise_for_error()
    out = res.output(0)
    assert out.columns.tolist() == ["URL", "Screenshot path", "Screenshot filename", "PDF"]
    assert out["Screenshot filename"].tolist() == [f"screenshot_{i}.png" for i in range(4)]
    assert [png_size(p) for p in out["Screenshot path"]] == [(1280, 720)] * 4
    assert [v["url"] for v in chrome.visits] == pd.read_csv(SAMPLE)["URL"].tolist()
    assert all(v["timeout"] == 3 and v["is_docker"] is False for v in chrome.visits)
    assert chrome.pdfs == [] and (out["PDF"].fillna("") == "").all()
    assert res.final_message == f"4 screenshots saved in {tmp_path}."


def test_pdf_with_the_default_name_one_page_per_screenshot(chrome, tmp_path):
    # The original failed with "can only concatenate str (not NoneType)" when the PDF file name was left empty
    res = run_block(HERE, SAMPLE, options(tmp_path, create_pdf=True, compression=True, resolution="1123x794",
                                          orientation="P"), is_docker=True).raise_for_error()
    out = res.output(0)
    pdf = os.path.join(str(tmp_path), "screenshots.pdf")
    assert out["PDF"].tolist() == [pdf] * 4 and os.path.exists(pdf)
    assert chrome.pdfs == [{"path": pdf, "orientation": "P", "resolution": "1123x794", "compressed": True,
                            "pages": [(794, 1123)] * 4}]
    assert all(v["is_docker"] for v in chrome.visits)
    run_block(HERE, SAMPLE, options(tmp_path, create_pdf=True, pdf_file_name="week 12")).raise_for_error()
    assert chrome.pdfs[-1]["path"].endswith("week 12.pdf") and chrome.pdfs[-1]["pages"] == [(1280, 720)] * 4


def test_credentials_keep_the_tab_and_stay_out_of_the_output(chrome, tmp_path):
    # The original dropped everything after the path (the #tab and any ?query) when adding credentials, and wrote
    # the address with user:password@ in it to the output
    df = pd.DataFrame({"URL": [TAB, "https://www.example.com/a?b=1"]})
    out = run_block(HERE, df, options(tmp_path, auth_username="bot", auth_password="Pa ss")).raise_for_error()
    assert [v["url"] for v in chrome.visits] == [
        "http://bot:Pa%20ss@127.0.0.1:24679/Sales/Monthly%20Review.iox/r/Board%20Pack/#Overview",
        "https://bot:Pa%20ss@www.example.com/a?b=1"]
    assert out.output(0)["URL"].tolist() == df["URL"].tolist()


def test_tinify_shrinks_the_pngs_after_the_pdf_is_made(chrome, tmp_path):
    res = run_block(HERE, SAMPLE, options(tmp_path, tinify=True, tinify_key="tk-123", tinify_width=640,
                                          create_pdf=True)).raise_for_error()
    assert [t["width"] for t in chrome.tinified] == [640] * 4 and chrome.tinified[0]["key"] == "tk-123"
    assert [png_size(p) for p in res.output(0)["Screenshot path"]] == [(640, 360)] * 4
    assert chrome.pdfs[0]["pages"] == [(1280, 720)] * 4
    for missing in ({"tinify_key": None}, {"tinify_width": None}):
        res = run_block(HERE, SAMPLE, options(tmp_path, tinify=True, **{"tinify_key": "k", "tinify_width": 9,
                                                                        **missing}))
        assert res.status == "aborted" and "Tinify needs" in res.final_message


def test_empty_input_makes_no_files(chrome, tmp_path):
    df = pd.DataFrame({"URL": pd.Series([], dtype=object)})
    out = run_block(HERE, df, options(tmp_path, create_pdf=True, pdf_file_name="x.pdf")).raise_for_error()
    assert len(out.output(0)) == 0 and out.output(0).columns.tolist()[:3] == ["URL", "Screenshot path",
                                                                              "Screenshot filename"]
    assert chrome.visits == [] and chrome.pdfs == [] and os.listdir(tmp_path) == []


def test_missing_urls_are_skipped_and_the_folder_is_created(chrome, tmp_path):
    folder = tmp_path / "shots"
    df = pd.DataFrame({"URL": [TAB, None, ""], "n": [1, None, 3]})
    res = run_block(HERE, df, options(folder)).raise_for_error()
    assert res.output(0)["Screenshot filename"].tolist() == ["screenshot_0.png"]
    assert os.listdir(folder) == ["screenshot_0.png"]
    assert res.final_message.endswith("2 records without a URL skipped.")


def test_bad_options_and_chrome_errors_abort(monkeypatch, chrome, tmp_path):
    assert run_block(HERE, None, options(tmp_path)).status == "aborted"
    res = run_block(HERE, SAMPLE, options(tmp_path, url_field=None))
    assert res.status == "aborted" and "Choose the field" in res.final_message
    res = run_block(HERE, SAMPLE, options(tmp_path, url_field="Address"))
    assert res.status == "aborted" and "'Address'" in res.final_message
    res = run_block(HERE, SAMPLE, options(tmp_path, folder_path=None))
    assert res.status == "aborted" and "output folder" in res.final_message
    res = run_block(HERE, SAMPLE, options(tmp_path, sleep_seconds=-2))
    assert res.status == "aborted" and "negative" in res.final_message
    failing = FakeChrome(fail_on="example.com")
    monkeypatch.setitem(sys.modules, "visokio_omniprint", failing.module())
    res = run_block(HERE, SAMPLE, options(tmp_path, auth_username="bot", auth_password="Secret1"))
    assert res.status == "aborted" and "record 4" in res.final_message and "ERR_NAME_NOT_RESOLVED" in res.final_message
    assert "Secret1" not in res.final_message


def test_many_pages(chrome, tmp_path):
    n = 500
    df = pd.DataFrame({"URL": [f"https://www.example.com/p/{i}" for i in range(n)]})
    t0 = time.time()
    out = run_block(HERE, df, options(tmp_path, resolution="1024x768", create_pdf=True)).raise_for_error()
    assert time.time() - t0 < 60
    assert len(out.output(0)) == n and len(chrome.pdfs[0]["pages"]) == n
