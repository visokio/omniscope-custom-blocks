import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "customer-comments.csv")
DF = pd.DataFrame({"t": ["The delivery was late. Late again!", "Delivery late, call back promised", "Great staff, great store", None, "Call back never came"],
                   "g": ["x", "x", "y", "y", "x"]})


def run(df, **opts):
    return run_block(HERE, df, {"text_field": "t", **opts})


def test_counts_stop_words_and_phrases():
    res = run(DF, min_documents=1).raise_for_error()
    t = res.output(0).set_index("Term")
    assert "the" not in t.index and "was" not in t.index
    assert t.loc["late", "Occurrences"] == 3 and t.loc["late", "Rows Using Term"] == 2
    assert t.loc["call back", "Words In Term"] == 2 and t.loc["call back", "Rows Using Term"] == 2
    assert t.loc["delivery late", "Rows Using Term"] == 2  # "was" removed between the words
    assert np.isclose(t.loc["late", "Share Of Rows"], 2 / 5)
    r = res.output(1)
    assert r["Word Count"].tolist() == [6, 5, 4, 0, 4] and pd.isna(r["Top Terms Used"].iloc[3])


def test_options():
    t = run(DF, min_documents=1, max_ngram=1).raise_for_error().output(0)
    assert (t["Words In Term"] == 1).all()
    t = run(DF, min_documents=1, remove_stop_words=False).raise_for_error().output(0)
    assert "the" in set(t["Term"])
    t = run(DF, min_documents=1, extra_stop_words="late, Great").raise_for_error().output(0)
    assert "late" not in set(t["Term"]) and "great" not in set(t["Term"])
    t = run(DF, min_documents=2).raise_for_error().output(0)
    assert set(t["Term"]) == {"delivery", "late", "call", "back", "call back", "delivery late"}
    t = run(DF, min_documents=1, top_n=3).raise_for_error().output(0)
    assert len(t) == 3
    t = run(pd.DataFrame({"t": ["Order 12345 arrived in 3 days", "Order 12345 arrived"]}), keep_numbers=True).raise_for_error().output(0)
    assert "12345" in set(t["Term"])


def test_groups_and_distinctiveness():
    df = pd.DataFrame({"t": ["hold music hold"] * 40 + ["quick delivery"] * 40 + ["fine thanks"] * 40, "g": ["a"] * 40 + ["b"] * 40 + ["a"] * 20 + ["b"] * 20})
    t = run(df, group_fields=["g"]).raise_for_error().output(0)
    a = t[t["g"] == "a"].set_index("Term")
    b = t[t["g"] == "b"].set_index("Term")
    assert a.loc["hold", "Distinctive"] == "Yes" and a.loc["hold", "Share Of Rows In Other Groups"] == 0
    assert b.loc["delivery", "Distinctive"] == "Yes" and "hold" not in b.index
    assert abs(a.loc["fine", "Distinctiveness (z)"]) < 1.96  # used equally in both groups


def test_sample_comments():
    res = run_block(HERE, SAMPLE, {"text_field": "Comment", "group_fields": ["Channel"]}).raise_for_error()
    t = res.output(0)
    top = t[t["Channel"] == "Contact Centre"].sort_values("Distinctiveness (z)", ascending=False)["Term"].head(5).tolist()
    assert "hold" in top
    assert len(res.output(1)) == 1800


def test_bad_inputs_and_empty():
    assert run(DF, text_field="nope").status == "aborted"
    assert run(DF, group_fields=["zz"]).status == "aborted"
    assert run(DF, max_ngram=9).status == "aborted"
    res = run(DF.iloc[0:0]).raise_for_error()
    assert len(res.output(0)) == 0 and len(res.output(1)) == 0
    res = run(pd.DataFrame({"t": [1, 2.5, None]}), keep_numbers=True, min_documents=1).raise_for_error()
    assert len(res.output(1)) == 3


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    words = [f"w{i}" for i in range(3000)]
    n = 100_000
    texts = [" ".join(rng.choice(words, 15)) for _ in range(n)]
    df = pd.DataFrame({"t": texts, "g": rng.choice(list("abcde"), n)})
    t0 = time.time()
    res = run(df, group_fields=["g"], keep_numbers=True, top_n=200).raise_for_error()
    assert time.time() - t0 < 120 and len(res.output(0)) == 1000
