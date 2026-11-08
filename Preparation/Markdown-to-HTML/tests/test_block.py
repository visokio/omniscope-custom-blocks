import os
import time

import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "product-descriptions.csv")


def run(df, **options):
    return run_block(HERE, df, options).raise_for_error().output(0)


def test_sample_descriptions():
    out = run(SAMPLE, MarkdownText="Description")
    assert len(out) == 7
    assert list(out.columns) == ["SKU", "Product", "Description", "HTML"]
    html = dict(zip(out["SKU"], out["HTML"]))
    assert "<strong>terracotta</strong>" in html["PL-30"] and html["PL-30"].count("<li>") == 3
    assert '<a href="https://example.com/guides/compost">growing guide</a>' in html["CP-50"]
    assert html["HR-01"].startswith("<h2>What's included</h2>") and "<ol>" in html["HR-01"]
    assert "<table>" in html["WC-09"] and html["WC-09"].count("<tr>") == 3
    assert "<blockquote>" in html["GL-12"]
    assert pd.isna(html["NT-04"])                                   # empty description stays empty
    assert "<br />" in html["HB-01"] and "<code>10 minutes</code>" in html["HB-01"]


def test_empty_values_no_longer_fail():
    # The original raised AttributeError on a missing value
    df = pd.DataFrame({"id": [1, 2], "md": ["*a*", None]})
    out = run(df, MarkdownText="md")
    assert out["HTML"].tolist()[0] == "<p><em>a</em></p>" and pd.isna(out["HTML"].iloc[1])


def test_input_fields_are_kept_by_default_and_can_be_dropped():
    # The original output only the HTML field, losing the link to the record it came from
    df = pd.DataFrame({"id": [7], "md": ["# Title"]})
    out = run(df, MarkdownText="md")
    assert out["id"].tolist() == [7] and out["HTML"].tolist() == ["<h1>Title</h1>"]
    out = run(df, MarkdownText="md", includeInput=False)
    assert list(out.columns) == ["HTML"]


def test_output_name_and_in_place():
    df = pd.DataFrame({"id": [1], "md": ["**b**"]})
    assert list(run(df, MarkdownText="md", outputField="Body HTML").columns) == ["id", "md", "Body HTML"]
    out = run(df, MarkdownText="md", outputField="md")
    assert list(out.columns) == ["id", "md"] and out["md"].tolist() == ["<p><strong>b</strong></p>"]
    res = run_block(HERE, df, {"MarkdownText": "md", "outputField": "id"})
    assert res.status == "aborted" and "already has a field" in res.final_message


def test_tables_need_the_extensions():
    md = "| a | b |\n|---|---|\n| 1 | 2 |"
    df = pd.DataFrame({"md": [md]})
    assert "<table>" in run(df, MarkdownText="md")["HTML"].iloc[0]
    assert "<table>" not in run(df, MarkdownText="md", extensions=False)["HTML"].iloc[0]


def test_footnote_numbers_restart_for_each_record():
    # One converter is reused for speed; reset() between records keeps footnotes apart
    df = pd.DataFrame({"md": ["A[^1]\n\n[^1]: one", "B[^1]\n\n[^1]: two"]})
    out = run(df, MarkdownText="md")["HTML"].tolist()
    assert "one" in out[0] and "two" not in out[0] and "two" in out[1] and "one" not in out[1]


def test_numbers_are_converted_as_text():
    out = run(pd.DataFrame({"n": [5, None]}), MarkdownText="n")
    assert out["HTML"].tolist()[0] == "<p>5</p>"


def test_empty_input_and_bad_options():
    df = pd.DataFrame({"id": pd.Series([], dtype="int64"), "md": pd.Series([], dtype=object)})
    out = run(df, MarkdownText="md")
    assert len(out) == 0 and list(out.columns) == ["id", "md", "HTML"]
    res = run_block(HERE, df, {"MarkdownText": None})
    assert res.status == "aborted" and "Choose" in res.final_message
    assert run_block(HERE, None, {"MarkdownText": "md"}).status == "aborted"


def test_large_input():
    n = 20_000
    md = "## Item {i}\n\nSome **bold** text with a [link](https://example.com/{i}).\n\n- one\n- two\n"
    df = pd.DataFrame({"id": range(n), "md": [md.format(i=i) for i in range(n)]})
    t0 = time.time()
    out = run(df, MarkdownText="md")
    assert time.time() - t0 < 60
    assert len(out) == n and out["HTML"].str.contains("<strong>bold</strong>").all()


def test_html_in_the_text_is_passed_through():
    # Documented in the README's limits: the block does not sanitise
    out = run(pd.DataFrame({"md": ["<script>x()</script>\n\nHi <b>there</b>"]}), MarkdownText="md")
    assert out["HTML"].iloc[0] == "<script>x()</script>\n\n<p>Hi <b>there</b></p>"
