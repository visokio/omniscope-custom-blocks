import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "engagement-survey.csv")
Q = ["q1", "q2"]


def run(inputs, **opts):
    return run_block(HERE, inputs, {"question_fields": Q, **opts})


def survey():
    return pd.DataFrame({"q1": ["Strongly agree", "agree", "Disagree", "Neither agree nor disagree", "AGREE"],
                         "q2": ["Strongly disagree", None, "n/a", "Agree.", "banana"], "seg": ["a", "a", "b", "b", "b"]})


def test_summary_metrics():
    res = run(survey()).raise_for_error()
    s = res.output(0).set_index("Question")
    assert s.loc["q1", "Responses"] == 5 and abs(s.loc["q1", "Top 2 Box"] - 0.6) < 1e-12
    assert abs(s.loc["q1", "Bottom 2 Box"] - 0.2) < 1e-12 and abs(s.loc["q1", "Net Score"] - 0.4) < 1e-12
    assert abs(s.loc["q1", "Mean Score"] - (5 + 4 + 2 + 3 + 4) / 5) < 1e-12
    assert s.loc["q2", "Responses"] == 2 and s.loc["q2", "No Answer"] == 2 and s.loc["q2", "Unrecognised"] == 1
    assert s.loc["q2", "Reliable"].startswith("No")


def test_distribution_diverging_and_long():
    res = run(survey()).raise_for_error()
    d = res.output(1)
    q1 = d[d.Question == "q1"].set_index("Answer")
    assert q1.loc["Agree", "Count"] == 2 and q1.loc["Disagree", "Diverging Share"] < 0 and q1.loc["Neither agree nor disagree", "Diverging Share"] == 0
    assert abs(q1["Share"].sum() - 1) < 1e-12
    long = res.output(2)
    assert len(long) == 10 and set(long["Answer"]) >= {"No answer", "Unrecognised", "Agree"}


def test_segments_numeric_custom_and_four_point():
    s = run(survey(), segment_fields=["seg"]).raise_for_error().output(0)
    assert len(s) == 4 and set(s["seg"]) == {"a", "b"}
    num = pd.DataFrame({"q1": [1, 2, 3, 4, 5, 5], "q2": [5, 4, 4, 4, 3, 1]})
    s = run(num, scale="NUMERIC").raise_for_error().output(0).set_index("Question")
    assert abs(s.loc["q1", "Top 2 Box"] - 0.5) < 1e-12
    c = pd.DataFrame({"q1": ["Poor", "Good", "Excellent"], "q2": ["Fair", "Fair", "Good"]})
    s = run(c, scale="CUSTOM", custom_labels="Poor, Fair, Good, Very good, Excellent").raise_for_error().output(0).set_index("Question")
    assert s.loc["q1", "Mean Score"] == (1 + 3 + 5) / 3
    f = pd.DataFrame({"q1": ["Agree", "Disagree"], "q2": ["Strongly agree", "Agree"]})
    s = run(f, scale="AGREE4").raise_for_error().output(0).set_index("Question")
    assert s.loc["q1", "Neutral"] == 0 and s.loc["q2", "Top 2 Box"] == 1


def test_sample_survey():
    q = [c for c in pd.read_csv(SAMPLE).columns if c not in ("Respondent ID", "Department", "Tenure")]
    res = run_block(HERE, SAMPLE, {"question_fields": q, "segment_fields": ["Department"]}).raise_for_error()
    s = res.output(0)
    assert len(s) == 8 * 5 and s["Responses"].min() > 30
    overall = run_block(HERE, SAMPLE, {"question_fields": q}).raise_for_error().output(0).set_index("Question")
    assert overall["Net Score"].idxmax() == "I understand how my work contributes to company goals"


def test_bad_options_and_empty():
    assert run(survey(), question_fields=[]).status == "aborted"
    assert run(survey(), scale="CUSTOM", custom_labels="Only").status == "aborted"
    assert run(survey(), segment_fields=["nope"]).status == "aborted"
    empty = survey().iloc[0:0]
    res = run(empty).raise_for_error()
    assert len(res.output(2)) == 0


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    L = ["Strongly disagree", "Disagree", "Neither agree nor disagree", "Agree", "Strongly agree"]
    df = pd.DataFrame({f"q{i}": rng.choice(L, 20_000) for i in range(10)})
    df["seg"] = rng.choice(list("abcdef"), 20_000)
    t0 = time.time()
    res = run_block(HERE, df, {"question_fields": [f"q{i}" for i in range(10)], "segment_fields": ["seg"]}).raise_for_error()
    assert time.time() - t0 < 60 and len(res.output(2)) == 200_000
