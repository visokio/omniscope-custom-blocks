"""Tests for Report to PowerPoint. Chrome is not started: the visokio_omniprint package is replaced by a stand-in
that records each page visited and writes a PNG the size of the page area Chrome would show. The PowerPoint file is
made by the real python-pptx and read back."""
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

pptx = pytest.importorskip("pptx")  # python-pptx: installed with visokio-omniprint on a server

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "report-tabs.csv")
TAB = "http://127.0.0.1:24679/Finance/Quarterly%20Review.iox/r/Quarterly%20Review/#Headlines"

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
    return {"url_field": "Report tab URL", "folder_path": str(folder), **kw}


def deck(path):
    prs = pptx.Presentation(path)
    pictures = [[s for s in slide.shapes if s.shape_type == 13] for slide in prs.slides]
    return prs, pictures


def test_sample_one_slide_per_tab_filled_by_its_screenshot(chrome, tmp_path):
    # The original made 4:3 slides (10 x 7.5 inches) with the picture 10 inches wide at the top, and ignored the
    # resolution and orientation; it also failed when the file name was left empty
    res = run_block(HERE, SAMPLE, options(tmp_path)).raise_for_error()
    out = res.output(0)
    path = os.path.join(str(tmp_path), "report.pptx")
    assert out.columns.tolist() == ["URL", "Screenshot path", "Screenshot filename", "PowerPoint file"]
    assert out["PowerPoint file"].tolist() == [path] * 5
    assert [png_size(p) for p in out["Screenshot path"]] == [(1280, 720)] * 5
    prs, pictures = deck(path)
    assert (prs.slide_width, prs.slide_height) == (12192000, 6858000)  # 13.333 x 7.5 inches, 16:9
    assert [len(p) for p in pictures] == [1] * 5
    pic = pictures[0][0]
    assert (pic.left, pic.top, pic.width, pic.height) == (0, 0, prs.slide_width, prs.slide_height)
    assert [v["url"] for v in chrome.visits] == pd.read_csv(SAMPLE)["Report tab URL"].tolist()
    assert res.final_message == f"report.pptx written to {tmp_path} with 5 slides."


def test_portrait_4_to_3_and_a_file_name_without_extension(chrome, tmp_path):
    res = run_block(HERE, SAMPLE, options(tmp_path, resolution="1024x768", orientation="P",
                                          output_file_name="Q3 board")).raise_for_error()
    prs, _ = deck(os.path.join(str(tmp_path), "Q3 board.pptx"))
    assert (prs.slide_width, prs.slide_height) == (9144000, 12192000)
    assert png_size(res.output(0)["Screenshot path"][0]) == (768, 1024)


def test_credentials_keep_the_tab_and_stay_out_of_the_output(chrome, tmp_path):
    # The original dropped the #tab when adding credentials (every slide showed the Report's first tab) and wrote
    # the address with user:password@ in it to the output
    df = pd.DataFrame({"Report tab URL": [TAB]})
    out = run_block(HERE, df, options(tmp_path, auth_username="bot", auth_password="Secret1")).raise_for_error()
    assert chrome.visits[0]["url"] == ("http://bot:Secret1@127.0.0.1:24679/Finance/Quarterly%20Review.iox/r/"
                                       "Quarterly%20Review/#Headlines")
    assert out.output(0)["URL"].tolist() == [TAB]


def test_tinify(chrome, tmp_path):
    res = run_block(HERE, SAMPLE, options(tmp_path, tinify=True, tinify_key="tk", tinify_width=960))
    assert [png_size(p) for p in res.raise_for_error().output(0)["Screenshot path"]] == [(960, 540)] * 5
    res = run_block(HERE, SAMPLE, options(tmp_path, tinify=True, tinify_key="tk"))
    assert res.status == "aborted" and "Tinify needs" in res.final_message


def test_empty_input_writes_no_file(chrome, tmp_path):
    df = pd.DataFrame({"Report tab URL": pd.Series([], dtype=object)})
    res = run_block(HERE, df, options(tmp_path, output_file_name="x.pptx")).raise_for_error()
    assert len(res.output(0)) == 0 and res.output(0).columns.tolist() == ["URL", "Screenshot path",
                                                                          "Screenshot filename", "PowerPoint file"]
    assert os.listdir(tmp_path) == [] and chrome.visits == []


def test_missing_urls_are_skipped_and_the_folder_is_created(chrome, tmp_path):
    folder = tmp_path / "decks"
    df = pd.DataFrame({"Report tab URL": [TAB, None, TAB]})
    res = run_block(HERE, df, options(folder)).raise_for_error()
    assert res.output(0)["Screenshot filename"].tolist() == ["screenshot_0.png", "screenshot_2.png"]
    assert len(deck(os.path.join(str(folder), "report.pptx"))[0].slides) == 2
    assert res.final_message.endswith("1 record without a URL skipped.")


def test_bad_options_and_chrome_errors_abort(monkeypatch, chrome, tmp_path):
    assert run_block(HERE, None, options(tmp_path)).status == "aborted"
    res = run_block(HERE, SAMPLE, options(tmp_path, url_field=None))
    assert res.status == "aborted" and "Choose the field" in res.final_message
    res = run_block(HERE, SAMPLE, options(tmp_path, url_field="URL"))
    assert res.status == "aborted" and "'URL'" in res.final_message
    res = run_block(HERE, SAMPLE, options(tmp_path, folder_path=""))
    assert res.status == "aborted" and "output folder" in res.final_message
    failing = FakeChrome(fail_on="#Costs")
    monkeypatch.setitem(sys.modules, "visokio_omniprint", failing.module())
    res = run_block(HERE, SAMPLE, options(tmp_path, auth_username="bot", auth_password="Secret1"))
    assert res.status == "aborted" and "record 3" in res.final_message and "Secret1" not in res.final_message


def test_many_tabs(chrome, tmp_path):
    n = 200
    df = pd.DataFrame({"Report tab URL": [f"{TAB}{i}" for i in range(n)]})
    t0 = time.time()
    out = run_block(HERE, df, options(tmp_path, resolution="1024x768")).raise_for_error().output(0)
    assert time.time() - t0 < 60
    assert len(out) == n and len(deck(out["PowerPoint file"][0])[0].slides) == n
