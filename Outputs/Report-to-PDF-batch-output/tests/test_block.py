"""Tests for Multi-tenant Report to PDF. Chrome is not started: the visokio_omniprint package is replaced by a
stand-in whose Pdf.create_pdf records the address it was asked to print and returns a few bytes, so the tests
check the print addresses, the file names and the files written."""
import importlib.util
import os
import sys
import time
import types

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "scenarios.csv")
REPO = os.path.dirname(os.path.dirname(HERE))
BASE = "http://127.0.0.1:24679/Sales/Regional%20Review.iox/r/Region%20Pack"


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
    return {"report": BASE + "/#Summary", "outputFolder": str(folder), **kw}


def test_sample_prints_one_pdf_per_scenario(printer, tmp_path):
    res = run_block(HERE, SAMPLE, options(tmp_path)).raise_for_error()
    out = res.output(0)
    assert out.columns.tolist() == ["Scenario", "URL", "PDF filename", "PDF path"]
    assert out["Scenario"].tolist() == ["north", "midlands", "south-east", "south-west", "scotland", "wales"]
    assert out["PDF filename"].tolist()[:2] == ["Region Pack-north.pdf", "Region Pack-midlands.pdf"]
    assert out["URL"].tolist()[0] == BASE + "/s/north/#Summary"
    assert printer.calls[0] == {"url": BASE + "/s/north/#device=printer&tab=Summary", "timeout": 3,
                                "is_docker": False}
    assert sorted(os.listdir(tmp_path)) == sorted(out["PDF filename"])
    assert res.final_message == f"6 PDF files written to {tmp_path}."


def test_credentials_open_the_page_but_stay_out_of_the_output(printer, tmp_path):
    # The original wrote the address with user:password@ in it to the output's URL field
    out = run_block(HERE, SAMPLE, options(tmp_path, auth_username="print.bot", auth_password="Secret1"))
    out = out.raise_for_error().output(0)
    assert printer.calls[0]["url"].startswith("http://print.bot:Secret1@127.0.0.1:24679/")
    assert not out["URL"].str.contains("Secret1").any()


def test_scenario_field_option_and_awkward_ids(printer, tmp_path):
    # The original only read a field called 'scenario' (KeyError otherwise), put IDs into the address as they
    # were and used them unchanged in file names
    df = pd.DataFrame({"Tenant": ["Acme Ltd", "R&D/Labs", None, 42]})
    res = run_block(HERE, df, options(tmp_path, scenarioField="Tenant", pageWidth=800)).raise_for_error()
    out = res.output(0)
    assert out["Scenario"].tolist() == ["Acme Ltd", "R&D/Labs", "42"]
    assert [c["url"] for c in printer.calls] == [
        BASE + "/s/Acme%20Ltd/#device=printer&pageWidth=800&tab=Summary",
        BASE + "/s/R%26D%2FLabs/#device=printer&pageWidth=800&tab=Summary",
        BASE + "/s/42/#device=printer&pageWidth=800&tab=Summary"]
    assert out["PDF filename"].tolist() == ["Region Pack-Acme Ltd.pdf", "Region Pack-R&D_Labs.pdf",
                                            "Region Pack-42.pdf"]
    assert res.final_message.endswith("1 record without a scenario skipped.")


def test_address_without_a_slash_before_the_tab(printer, tmp_path):
    # The original cut the address at its last '/', so '.../r/Region%20Pack#Summary' printed '.../r/s/north/'
    run_block(HERE, SAMPLE, options(tmp_path, report=BASE + "#Summary")).raise_for_error()
    assert printer.calls[0]["url"] == BASE + "/s/north/#device=printer&tab=Summary"
    run_block(HERE, SAMPLE, options(tmp_path, report=BASE)).raise_for_error()
    assert printer.calls[-1]["url"] == BASE + "/s/wales/#device=printer"


def test_duplicate_scenarios_do_not_overwrite(printer, tmp_path):
    df = pd.DataFrame({"scenario": ["north", "north"]})
    out = run_block(HERE, df, options(tmp_path)).raise_for_error().output(0)
    assert out["PDF filename"].tolist() == ["Region Pack-north.pdf", "Region Pack-north-2.pdf"]


def test_a_failed_print_stops_with_the_scenario_and_hides_the_password(monkeypatch, tmp_path):
    fake = FakePrinter(fail_on="/s/scotland/")
    monkeypatch.setitem(sys.modules, "visokio_omniprint", fake.module())
    res = run_block(HERE, SAMPLE, options(tmp_path, auth_username="bot", auth_password="Secret1"))
    assert res.status == "aborted" and "'scotland'" in res.final_message and "record 5" in res.final_message
    assert "Secret1" not in res.final_message


def test_empty_input(printer, tmp_path):
    df = pd.DataFrame({"scenario": pd.Series([], dtype=object)})
    out = run_block(HERE, df, options(tmp_path)).raise_for_error().output(0)
    assert len(out) == 0 and out.columns.tolist() == ["Scenario", "URL", "PDF filename", "PDF path"]
    assert printer.calls == []


def test_bad_options_abort(printer, tmp_path):
    assert run_block(HERE, None, options(tmp_path)).status == "aborted"
    res = run_block(HERE, pd.DataFrame({"Region": ["North"]}), options(tmp_path))
    assert res.status == "aborted" and "'scenario'" in res.final_message
    res = run_block(HERE, SAMPLE, options(tmp_path, report=None))
    assert res.status == "aborted" and "address" in res.final_message
    res = run_block(HERE, SAMPLE, options(tmp_path, report="Region Pack"))
    assert res.status == "aborted" and "not a web address" in res.final_message
    res = run_block(HERE, SAMPLE, options(tmp_path, report=BASE + "/s/north/#Summary"))
    assert res.status == "aborted" and "without a scenario" in res.final_message
    res = run_block(HERE, SAMPLE, options(tmp_path, outputFolder=None))
    assert res.status == "aborted" and "output folder" in res.final_message
    assert printer.calls == []


def test_folder_is_created_and_many_scenarios(printer, tmp_path):
    folder = tmp_path / "out" / "pdf"
    n = 2_000
    df = pd.DataFrame({"scenario": [f"customer-{i}" for i in range(n)]})
    t0 = time.time()
    out = run_block(HERE, df, options(folder)).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert len(out) == n and len(os.listdir(folder)) == n
