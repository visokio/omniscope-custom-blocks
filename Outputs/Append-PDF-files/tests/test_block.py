"""Tests for the Append PDF files block, on the invented PDFs in sample-data/pdfs/ (sample-data/make_sample_pdfs.py)."""
import importlib.util
import os
import shutil
import time

import pandas as pd
import pytest
from pypdf import PdfReader, PdfWriter

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
PDFS = os.path.join(HERE, "sample-data", "pdfs")
LIST = os.path.join(HERE, "sample-data", "report-sections.csv")

spec = importlib.util.spec_from_file_location("make_sample_pdfs", os.path.join(HERE, "sample-data", "make_sample_pdfs.py"))
maker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maker)


@pytest.fixture
def folder(tmp_path):
    """A copy of the sample PDFs, so the combined file is written outside the repository."""
    target = tmp_path / "pdfs"
    shutil.copytree(PDFS, target)
    return target


def combine(inputs, folder, **options):
    folder = str(folder)
    return run_block(HERE, inputs, {"input_folder": folder, "output_folder": folder, "pdf_file_names": "File name",
                                    **options})


def texts(path):
    return [p.extract_text() for p in PdfReader(path).pages]


def bookmarks(path):
    reader = PdfReader(path)
    return [(o.title, reader.get_destination_page_number(o) + 1) for o in reader.outline]


def test_sample_board_pack(folder):
    res = combine(LIST, folder, title="Bookmark", file_name="board-pack.pdf").raise_for_error()
    out = res.output(0)
    combined = folder / "board-pack.pdf"
    assert out["Combined PDF"].tolist() == [str(combined)] * 5
    assert out["Pages"].tolist() == [1, 2, 1, 3, 1]
    assert out["First page"].tolist() == [1, 2, 4, 5, 8]
    assert list(out.columns) == ["Section", "File name", "Bookmark", "Combined PDF", "Pages", "First page"]
    pages = texts(combined)
    assert len(pages) == 8
    assert pages[0].startswith("Harbour Lane Foods") and pages[3] == "Cash flow: thirteen-week forecast"
    # the appendix has no title, so no bookmark (the original block failed on the empty title)
    assert bookmarks(combined) == [("Cover", 1), ("Trading summary", 2), ("Cash flow", 4), ("Risks and actions", 5)]
    assert "8 pages" in res.final_message


def test_no_bookmarks_and_name_without_extension(folder):
    res = combine(LIST, folder, file_name="pack").raise_for_error()
    assert (folder / "pack.pdf").exists() and bookmarks(folder / "pack.pdf") == []
    assert res.output(0)["Combined PDF"].iloc[0].endswith("pack.pdf")


def test_record_order_decides_page_order(folder):
    df = pd.read_csv(LIST).iloc[::-1]
    combine(df, folder, file_name="reversed.pdf").raise_for_error()
    pages = texts(folder / "reversed.pdf")
    assert pages[0] == "Appendix: definitions" and pages[-1].startswith("Harbour Lane Foods")


def test_folder_given_as_a_file_in_it_and_output_folder_defaults_to_it(folder):
    # The folder options are file pickers; picking a file inside the folder used to give paths like a.pdf/b.pdf
    res = run_block(HERE, LIST, {"input_folder": str(folder / "01-cover.pdf"), "pdf_file_names": "File name"})
    res.raise_for_error()
    assert (folder / "combined.pdf").exists()


def test_full_paths_without_a_folder(folder, tmp_path):
    df = pd.DataFrame({"File name": [str(folder / "03-cash-flow.pdf"), str(folder / "01-cover.pdf")]})
    out_dir = tmp_path / "out" / "new"
    res = run_block(HERE, df, {"pdf_file_names": "File name", "output_folder": str(out_dir)}).raise_for_error()
    assert len(texts(out_dir / "combined.pdf")) == 2  # the output folder is created
    assert res.output(0)["First page"].tolist() == [1, 2]


def test_numbers_as_bookmark_titles(folder):
    df = pd.DataFrame({"File name": ["01-cover.pdf", "03-cash-flow.pdf"], "Year": [2024, 2025]})
    combine(df, folder, title="Year").raise_for_error()
    assert bookmarks(folder / "combined.pdf") == [("2024", 1), ("2025", 2)]


def test_bookmarks_inside_the_files_are_kept_under_the_new_one(folder):
    inner = PdfWriter(clone_from=str(folder / "04-risks.pdf"))
    inner.add_outline_item("Energy costs", 1)
    with open(folder / "risks-with-bookmarks.pdf", "wb") as fh:
        inner.write(fh)
    df = pd.DataFrame({"File name": ["01-cover.pdf", "risks-with-bookmarks.pdf"], "Title": ["Cover", "Risks"]})
    combine(df, folder, title="Title").raise_for_error()
    reader = PdfReader(folder / "combined.pdf")
    top, nested = reader.outline[1], reader.outline[2]
    assert top.title == "Risks" and [(o.title, reader.get_destination_page_number(o) + 1) for o in nested] == \
        [("Energy costs", 3)]


def test_missing_files_abort_with_their_names(folder):
    df = pd.DataFrame({"File name": ["01-cover.pdf", "missing-a.pdf", "missing-b.pdf"]})
    res = combine(df, folder)
    assert res.status == "aborted" and "2 PDF file(s) not found" in res.final_message
    assert "missing-a.pdf" in res.final_message and not (folder / "combined.pdf").exists()
    res = combine(pd.DataFrame({"File name": ["01-cover.pdf", None]}), folder)
    assert res.status == "aborted" and "Record 2 has no PDF file name" in res.final_message


def test_files_that_are_not_pdfs_or_have_a_password(folder):
    (folder / "notes.pdf").write_text("not a pdf")
    res = combine(pd.DataFrame({"File name": ["01-cover.pdf", "notes.pdf"]}), folder)
    assert res.status == "aborted" and "notes.pdf" in res.final_message
    locked = PdfWriter(clone_from=str(folder / "01-cover.pdf"))
    locked.encrypt("secret")
    with open(folder / "locked.pdf", "wb") as fh:
        locked.write(fh)
    res = combine(pd.DataFrame({"File name": ["locked.pdf"]}), folder)
    assert res.status == "aborted" and "password" in res.final_message


def test_empty_input_writes_no_file(folder):
    df = pd.DataFrame({"File name": pd.Series([], dtype=object)})
    res = combine(df, folder).raise_for_error()
    assert len(res.output(0)) == 0 and "Pages" in res.output(0).columns
    assert not (folder / "combined.pdf").exists()


def test_missing_input_and_options():
    assert run_block(HERE, None, {"pdf_file_names": "File name"}).status == "aborted"
    res = run_block(HERE, LIST, {"pdf_file_names": None})
    assert res.status == "aborted" and "Choose" in res.final_message


def test_many_files(tmp_path):
    for k in range(400):
        maker.write_pdf(tmp_path / f"part-{k:03d}.pdf", [f"Part {k}", f"Part {k} continued"])
    df = pd.DataFrame({"File name": [f"part-{k:03d}.pdf" for k in range(400)], "Title": [f"Part {k}" for k in range(400)]})
    t0 = time.time()
    res = combine(df, tmp_path, title="Title").raise_for_error()
    assert time.time() - t0 < 60
    assert res.output(0)["First page"].iloc[-1] == 799
    assert len(PdfReader(tmp_path / "combined.pdf").pages) == 800


def test_placeholder_is_the_block_output_for_the_sample(folder):
    # The demo shows sample-data/placeholder.csv in place of the block's Combined output: it must stay identical,
    # apart from the folder in Combined PDF (the placeholder was made with the PDFs in /reports/pdfs).
    out = combine(LIST, folder, title="Bookmark", file_name="board-pack.pdf").raise_for_error().output(0)
    expected = pd.read_csv(os.path.join(HERE, "sample-data", "placeholder.csv"))
    assert expected["Combined PDF"].eq("/reports/pdfs/board-pack.pdf").all()
    out = out.assign(**{"Combined PDF": "/reports/pdfs/board-pack.pdf"})
    pd.testing.assert_frame_equal(out.reset_index(drop=True), expected, check_dtype=False)
