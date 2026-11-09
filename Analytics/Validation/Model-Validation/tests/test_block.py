import os
import time

import numpy as np
import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "ticket-predictions.csv")
OPTS = {"ground_truth": "Actual Team", "prediction": "Predicted Team"}
AB = {"ground_truth": "actual", "prediction": "predicted"}
SCORE_FIELDS = ["Class", "Actual records", "Predicted records", "Correct", "Precision", "Recall", "F1 score"]


def run(df, opts=AB):
    return run_block(HERE, df, opts).raise_for_error()


def test_sample_tickets():
    # The original failed on the two tickets with no prediction
    res = run_block(HERE, SAMPLE, OPTS).raise_for_error()
    matrix, scores = res.output(0), res.output(1)
    assert list(matrix.columns) == ["Actual class", "Account", "Billing", "Complaints", "Delivery", "Technical",
                                    "(no prediction)"]
    m = matrix.set_index("Actual class")
    assert m.loc["Technical"].tolist() == [3, 1, 0, 0, 36, 0]
    assert m.loc["Complaints"].tolist() == [2, 0, 0, 2, 0, 0]
    assert m["(no prediction)"].sum() == 2 and int(np.trace(m[m.index.tolist()].to_numpy())) == 99
    assert list(scores.columns) == SCORE_FIELDS
    s = scores.set_index("Class").round(3)
    assert s.loc["Complaints"].tolist() == [4, 0, 0, 0.0, 0.0, 0.0]
    assert s.loc["Technical", ["Precision", "Recall", "F1 score"]].tolist() == [0.9, 0.9, 0.9]
    assert s.loc["Macro average", ["Precision", "Recall", "F1 score"]].tolist() == [0.663, 0.686, 0.672]
    assert s.loc["Weighted average", ["Precision", "Recall", "F1 score"]].tolist() == [0.816, 0.825, 0.818]
    assert s.loc["Micro average", ["Precision", "Recall", "F1 score"]].tolist() == [0.839, 0.825, 0.832]
    assert res.final_message.startswith("Accuracy 82.5%: 99 of 120") and "2 records with no prediction" in res.final_message


def test_a_class_that_is_never_predicted_is_in_the_matrix():
    # The original took the classes from the predictions only, so "c" (never predicted) had no row and
    # its records vanished from the matrix
    df = pd.DataFrame({"actual": ["a", "a", "b", "b", "c", "c"], "predicted": ["a", "a", "b", "a", "b", "a"]})
    res = run(df)
    m = res.output(0).set_index("Actual class")
    assert m.index.tolist() == ["a", "b", "c"] and list(m.columns) == ["a", "b", "c"]
    assert m.loc["c"].tolist() == [1, 1, 0] and m.to_numpy().sum() == 6


def test_scores_match_scikit_learn():
    metrics = pytest.importorskip("sklearn.metrics")
    rng = np.random.default_rng(1)
    actual = rng.choice(["x", "y", "z", "w"], 500, p=[0.4, 0.3, 0.2, 0.1])
    predicted = np.where(rng.random(500) < 0.7, actual, rng.choice(["x", "y", "z"], 500))
    s = run(pd.DataFrame({"actual": actual, "predicted": predicted})).output(1).set_index("Class")
    for name, avg in (("Macro average", "macro"), ("Weighted average", "weighted"), ("Micro average", "micro")):
        expected = metrics.precision_recall_fscore_support(actual, predicted, average=avg, zero_division=0)[:3]
        assert np.allclose(s.loc[name, ["Precision", "Recall", "F1 score"]].astype(float), expected), name
    per_class = metrics.precision_recall_fscore_support(actual, predicted, labels=["w", "x", "y", "z"],
                                                        zero_division=0)
    assert np.allclose(s.loc[["w", "x", "y", "z"], "Precision"], per_class[0])
    assert s.loc[["w", "x", "y", "z"], "Actual records"].tolist() == per_class[3].tolist()


def test_numbers_and_text_are_the_same_class():
    # The original raised "Mix of label input types" when one field held numbers and the other text
    df = pd.DataFrame({"actual": [1, 2, 10, 2], "predicted": ["1", "2", "2", "10"]})
    res = run(df)
    m = res.output(0)
    assert list(m.columns) == ["Actual class", "1", "2", "10"]  # numeric order, not "1", "10", "2"
    assert m["Actual class"].tolist() == ["1", "2", "10"]
    assert res.final_message.startswith("Accuracy 50.0%")
    floats = run(pd.DataFrame({"actual": [0, 1, 1], "predicted": [0.0, 1.0, 0.0]})).output(0)
    assert list(floats.columns) == ["Actual class", "0", "1"]


def test_missing_actual_values_are_left_out():
    df = pd.DataFrame({"actual": ["a", None, "b", "b"], "predicted": ["a", "b", "b", None]})
    res = run(df)
    m = res.output(0).set_index("Actual class")
    assert m.to_numpy().sum() == 3 and m.loc["b", "(no prediction)"] == 1
    assert "1 records with no actual value were left out" in res.final_message


def test_booleans():
    df = pd.DataFrame({"actual": [True, True, False, False], "predicted": [True, False, False, False]})
    s = run(df).output(1).set_index("Class")
    assert s.loc["True", "Recall"] == 0.5 and s.loc["False", "Precision"] == pytest.approx(2 / 3)


def test_empty_input():
    df = pd.DataFrame({"actual": pd.Series([], dtype=object), "predicted": pd.Series([], dtype=object)})
    res = run(df)
    assert len(res.output(0)) == 0 and list(res.output(0).columns) == ["Actual class"]
    assert len(res.output(1)) == 0 and list(res.output(1).columns) == SCORE_FIELDS
    assert "No records" in res.final_message


def test_bad_set_ups_abort():
    df = pd.DataFrame({"actual": ["a"], "predicted": ["a"]})
    res = run_block(HERE, None, AB)
    assert res.status == "aborted" and "Connect" in res.final_message
    res = run_block(HERE, df, {"ground_truth": None, "prediction": "predicted"})
    assert res.status == "aborted" and "Actual values" in res.final_message
    res = run_block(HERE, df, {"ground_truth": "actual", "prediction": "nope"})
    assert res.status == "aborted" and "nope" in res.final_message


def test_large_input():
    n = 200_000
    rng = np.random.default_rng(0)
    actual = rng.integers(0, 20, n)
    predicted = np.where(rng.random(n) < 0.8, actual, rng.integers(0, 20, n))
    t0 = time.time()
    res = run(pd.DataFrame({"actual": actual, "predicted": predicted}))
    assert time.time() - t0 < 30
    assert res.output(0).shape == (20, 21) and res.output(1)["Actual records"].iloc[:20].sum() == n
