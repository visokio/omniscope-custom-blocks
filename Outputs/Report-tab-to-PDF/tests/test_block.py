"""Tests for Report tab to PDF. Chrome is not started: the visokio_omniprint package is replaced by a stand-in
whose Pdf.create_pdf records the address it was asked to print and returns a few bytes, so the tests check the
print addresses, the file names and the files written."""
import importlib.util
import os
import sys
import time
import types

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "report-tabs.csv")
REPO = os.path.dirname(os.path.dirname(HERE))
BASE = "http://127.0.0.1:24679/Sales/Monthly%20Review.iox/r/Board%20Pack"


def real_tools():
    """The real Tools class (pure URL handling, no Chrome), which the original script used."""
    path = os.path.join(REPO, "visokio-omniprint", "visokio_omniprint", "Tools.py")
    spec = importlib.util.spec_from_file_location("omniprint_tools_for_tests", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Tools


class FakePrinter:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def module(self):
        printer = self

        class Pdf:
            def create_pdf(self, url, timeout, is_docker):
                printer.calls.append({"url": url, "timeout": timeout, "is_docker": is_docker})
                if printer.fail_on and printer.fail_on in url:
                    raise Exception(f"Message: unknown error: net::ERR_CONNECTION_REFUSED loading {url}")
                return b"%PDF-1.4\n% stand-in for " + url.encode()

        mod = types.ModuleType("visokio_omniprint")
        mod.Pdf = Pdf
        mod.Tools = real_tools()
        return mod


@pytest.fixture
def printer(monkeypatch):
    fake = FakePrinter()
    monkeypatch.setitem(sys.modules, "visokio_omniprint", fake.module())
    return fake


def options(folder, **kw):
    return {"report": "Report tab URL", "fileName": "File name", "outputFolder": str(folder), **kw}


def test_sample_prints_one_pdf_per_tab(printer, tmp_path):
    res = run_block(HERE, SAMPLE, options(tmp_path)).raise_for_error()
    out = res.output(0)
    assert out.columns.tolist() == ["URL", "PDF filename", "PDF path"]
    assert out["PDF filename"].tolist() == ["2025-03 Overview.pdf", "2025-03 Regions.pdf", "2025-03 Products.pdf",
                                            "2025-03 Margins.pdf", "Board Pack-Customers-4.pdf"]
    assert out["URL"].tolist()[0] == BASE + "/#Overview"
    assert [c["url"] for c in printer.calls] == [f"{BASE}/#device=printer&tab={t}"
                                                 for t in ("Overview", "Regions", "Products", "Margins", "Customers")]
    assert all(c["timeout"] == 3 and c["is_docker"] is False for c in printer.calls)
    for path in out["PDF path"]:
        assert os.path.dirname(path) == str(tmp_path)
        with open(path, "rb") as fh:
            assert fh.read().startswith(b"%PDF")
    assert res.final_message == f"5 PDF files written to {tmp_path}."


def test_default_names_page_size_delay_and_docker(printer, tmp_path):
    df = pd.DataFrame({"u": [BASE + "/#Sales%20by%20Region&filter=x", BASE + "/"]})
    res = run_block(HERE, df, {"report": "u", "outputFolder": str(tmp_path), "pageWidth": 1123, "pageHeight": 794,
                               "chromeDelay": 1}, is_docker=True).raise_for_error()
    assert res.output(0)["PDF filename"].tolist() == ["Board Pack-Sales by Region-0.pdf", "Board Pack-1.pdf"]
    assert printer.calls[0] == {"url": f"{BASE}/#device=printer&pageWidth=1123&pageHeight=794"
                                       "&tab=Sales%20by%20Region&filter=x", "timeout": 1, "is_docker": True}
    assert printer.calls[1]["url"] == f"{BASE}/#device=printer&pageWidth=1123&pageHeight=794"


def test_a_multi_tenant_scenario_address(printer, tmp_path):
    df = pd.DataFrame({"u": [BASE + "/s/north/#Summary"]})
    out = run_block(HERE, df, {"report": "u", "outputFolder": str(tmp_path)}).raise_for_error().output(0)
    assert printer.calls[0]["url"] == f"{BASE}/s/north/#device=printer&tab=Summary"
    assert out["PDF filename"].tolist() == ["Board Pack-north-Summary-0.pdf"]


def test_address_without_a_slash_before_the_tab(printer, tmp_path):
    # The original cut the address at its last '/', so '.../r/Board%20Pack#Regions' printed '.../r/#device=printer'
    # (not the Report) and named the file 'r-Regions-0.pdf'
    df = pd.DataFrame({"u": [BASE + "#Regions", BASE]})
    out = run_block(HERE, df, {"report": "u", "outputFolder": str(tmp_path)}).raise_for_error().output(0)
    assert [c["url"] for c in printer.calls] == [f"{BASE}/#device=printer&tab=Regions", f"{BASE}/#device=printer"]
    assert out["PDF filename"].tolist() == ["Board Pack-Regions-0.pdf", "Board Pack-1.pdf"]


def test_file_names_from_the_field(printer, tmp_path):
    # The original wrote 'a.pdf.pdf' for a name ending in .pdf, 'nan.pdf' for a missing name, overwrote the first
    # of two records with the same name, and failed on a name with '/'
    df = pd.DataFrame({"u": [BASE + "/#A", BASE + "/#B", BASE + "/#C", BASE + "/#D", BASE + "/#E"],
                       "n": ["a.pdf", None, "same", "same", "North/South: Q1"]})
    out = run_block(HERE, df, {"report": "u", "fileName": "n", "outputFolder": str(tmp_path)})
    names = out.raise_for_error().output(0)["PDF filename"].tolist()
    assert names == ["a.pdf", "Board Pack-B-1.pdf", "same.pdf", "same-2.pdf", "North_South_ Q1.pdf"]
    assert sorted(os.listdir(tmp_path)) == sorted(names)


def test_credentials_open_the_page_but_stay_out_of_the_output(printer, tmp_path):
    df = pd.DataFrame({"u": [BASE + "/#Overview"]})
    out = run_block(HERE, df, {"report": "u", "outputFolder": str(tmp_path), "auth_username": "print.bot",
                               "auth_password": "p@ss/w:rd"}).raise_for_error().output(0)
    assert printer.calls[0]["url"] == ("http://print.bot:p%40ss%2Fw%3Ard@127.0.0.1:24679/Sales/Monthly%20Review.iox"
                                       "/r/Board%20Pack/#device=printer&tab=Overview")
    assert out["URL"].tolist() == [BASE + "/#Overview"]
    # a username without a password is not used
    run_block(HERE, df, {"report": "u", "outputFolder": str(tmp_path), "auth_username": "print.bot"})
    assert printer.calls[1]["url"].startswith("http://127.0.0.1")


def test_a_failed_print_stops_with_the_record_and_hides_the_password(monkeypatch, tmp_path):
    fake = FakePrinter(fail_on="Regions")
    monkeypatch.setitem(sys.modules, "visokio_omniprint", fake.module())
    res = run_block(HERE, SAMPLE, options(tmp_path, auth_username="bot", auth_password="Secret1"))
    assert res.status == "aborted"
    assert "record 2" in res.final_message and "ERR_CONNECTION_REFUSED" in res.final_message
    assert "Secret1" not in res.final_message and "***" in res.final_message


def test_empty_input_writes_no_files(printer, tmp_path):
    # The original output a table with no fields at all
    df = pd.DataFrame({"Report tab URL": pd.Series([], dtype=object), "File name": pd.Series([], dtype=object)})
    out = run_block(HERE, df, options(tmp_path)).raise_for_error().output(0)
    assert len(out) == 0 and out.columns.tolist() == ["URL", "PDF filename", "PDF path"]
    assert printer.calls == [] and os.listdir(tmp_path) == []


def test_missing_urls_are_skipped_and_the_folder_is_created(printer, tmp_path):
    # The original failed on a missing URL ('float' object has no attribute 'rsplit') and on a folder that
    # didn't exist yet
    folder = tmp_path / "new" / "pdfs"
    df = pd.DataFrame({"u": [BASE + "/#A", None, "  "]})
    res = run_block(HERE, df, {"report": "u", "outputFolder": str(folder)}).raise_for_error()
    assert len(res.output(0)) == 1 and os.listdir(folder) == ["Board Pack-A-0.pdf"]
    assert res.final_message.endswith("2 records without a URL skipped.")


def test_bad_options_and_values_abort(printer, tmp_path):
    df = pd.DataFrame({"u": [BASE + "/#A"], "n": [1]})
    assert "Connect" in run_block(HERE, None, options(tmp_path)).final_message
    res = run_block(HERE, df, {"report": None, "outputFolder": str(tmp_path)})
    assert res.status == "aborted" and "Choose the field" in res.final_message
    res = run_block(HERE, df, {"report": "nope", "outputFolder": str(tmp_path)})
    assert res.status == "aborted" and "'nope'" in res.final_message
    res = run_block(HERE, df, {"report": "u", "outputFolder": None})
    assert res.status == "aborted" and "output folder" in res.final_message
    res = run_block(HERE, df, {"report": "u", "outputFolder": str(tmp_path), "chromeDelay": -1})
    assert res.status == "aborted" and "negative" in res.final_message
    res = run_block(HERE, pd.DataFrame({"u": ["Board Pack"]}), {"report": "u", "outputFolder": str(tmp_path)})
    assert res.status == "aborted" and "not a web address" in res.final_message
    # a whole-number file name field is used as text
    out = run_block(HERE, df, {"report": "u", "fileName": "n", "outputFolder": str(tmp_path)})
    assert out.raise_for_error().output(0)["PDF filename"].tolist() == ["1.pdf"]
    assert printer.calls[-1]["url"] == f"{BASE}/#device=printer&tab=A"


def test_many_records(printer, tmp_path):
    n = 2_000
    df = pd.DataFrame({"u": [f"{BASE}/#Tab{i}" for i in range(n)]})
    t0 = time.time()
    out = run_block(HERE, df, {"report": "u", "outputFolder": str(tmp_path)}).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert len(out) == n and out["PDF filename"].is_unique and len(os.listdir(tmp_path)) == n
