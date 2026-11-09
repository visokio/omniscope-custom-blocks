import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
DATA = os.path.join(HERE, "sample-data")
HISTORY = os.path.join(DATA, "pump-history.csv")
READINGS = os.path.join(DATA, "pump-readings.csv")
INSPECTED = os.path.join(DATA, "pump-readings-inspected.csv")
OPTS = {"fieldToPredict": "Condition"}


def two_groups(n=100, seed=0, scale_big=1000.0):
    """Class depends on 'small' (units); 'big' is noise in thousands."""
    rng = np.random.default_rng(seed)
    cls = rng.integers(0, 2, n)
    return pd.DataFrame({"id": np.arange(n), "small": rng.normal(cls * 3.0, 0.5),
                         "big": rng.normal(5 * scale_big, scale_big, n), "cls": np.where(cls == 1, "B", "A")})


def test_sample_predicts_the_new_pumps():
    # The original raised KeyError: it needed the Field to predict on the records to predict
    res = run_block(HERE, [HISTORY, READINGS], OPTS).raise_for_error()
    out = res.output(0)
    assert len(out) == 30
    assert list(out.columns) == ["Pump", "Site", "Vibration", "Temperature", "Pressure", "Runtime Hours", "Prediction"]
    assert out["Prediction"].value_counts().to_dict() == {"Normal": 16, "Worn": 8, "Faulty": 5}
    # the pump whose vibration sensor did not report keeps its place, with no prediction
    assert pd.isna(out.loc[out["Pump"] == "P-2008", "Prediction"]).all()
    truth = pd.read_csv(INSPECTED)
    both = out.merge(truth, on="Pump").dropna(subset=["Prediction"])
    assert (both["Prediction"] == both["Condition"]).all()  # 29 of 29 match the engineers' findings
    assert "Trained on 150 records (4 fields)" in res.final_message and "1 left empty" in res.final_message


def test_no_second_input_predicts_the_training_records():
    out = run_block(HERE, [HISTORY], OPTS).raise_for_error().output(0)
    assert len(out) == 150 and "Condition" in out.columns
    assert (out["Prediction"] == out["Condition"]).mean() > 0.95


def test_fields_are_standardised():
    # The original did not scale the fields: with one field in thousands, every record got the same prediction
    train, new = two_groups(seed=0), two_groups(seed=1)
    opts = {"fieldToPredict": "cls", "useAllNumericFields": False, "fieldsToUse": ["small", "big"]}
    out = run_block(HERE, [train, new], opts).raise_for_error().output(0)
    assert out["Prediction"].nunique() == 2
    assert (out["Prediction"] == new["cls"]).mean() > 0.9


def test_a_numeric_field_to_predict_is_not_used_to_predict_itself():
    # The original added a numeric Field to predict to the fields to predict from (with "Use all numeric
    # fields"), so it predicted the answer from the answer, and the records to predict had to contain it
    rng = np.random.default_rng(3)
    train = pd.DataFrame({"noise": rng.normal(size=300), "label": rng.integers(0, 2, 300)})
    out = run_block(HERE, [train], {"fieldToPredict": "label"}).raise_for_error().output(0)
    assert (out["Prediction"] == out["label"]).mean() < 0.9
    new = pd.DataFrame({"noise": rng.normal(size=5)})
    out = run_block(HERE, [train, new], {"fieldToPredict": "label"}).raise_for_error().output(0)
    assert len(out) == 5 and str(out["Prediction"].dtype) == "Int64"


def test_predictions_stay_on_their_records_when_values_are_missing():
    # The original dropped records with missing values and then pasted the predictions back by position,
    # so records after a gap got another record's prediction
    train = two_groups(scale_big=1.0)
    new = two_groups(n=20, seed=5, scale_big=1.0)
    new.loc[3, "small"] = np.nan
    opts = {"fieldToPredict": "cls", "useAllNumericFields": False, "fieldsToUse": ["small", "big"]}
    out = run_block(HERE, [train, new.drop(columns="cls")], opts).raise_for_error().output(0)
    assert len(out) == 20 and out["id"].tolist() == list(range(20))
    assert pd.isna(out.loc[3, "Prediction"])
    ok = out.drop(index=3)
    assert (ok["Prediction"] == new.drop(index=3)["cls"]).all()


def test_training_records_with_missing_values_are_skipped():
    train = two_groups()
    train.loc[[1, 2], "small"] = np.nan
    train.loc[4, "cls"] = None
    res = run_block(HERE, [train], {"fieldToPredict": "cls"}).raise_for_error()
    assert "Trained on 97 records" in res.final_message
    assert len(res.output(0)) == 100


def test_chosen_fields_and_an_existing_prediction_field():
    df = two_groups()
    df["Prediction"] = "old"
    opts = {"fieldToPredict": "cls", "useAllNumericFields": False, "fieldsToUse": ["small"]}
    out = run_block(HERE, [df], opts).raise_for_error().output(0)
    assert list(out.columns).count("Prediction") == 1 and "old" not in set(out["Prediction"])
    assert (out["Prediction"] == out["cls"]).mean() > 0.9


def test_empty_records_to_predict():
    train = two_groups()
    out = run_block(HERE, [train, train.iloc[:0].drop(columns="cls")], {"fieldToPredict": "cls"})
    out = out.raise_for_error().output(0)
    assert len(out) == 0 and "Prediction" in out.columns


def test_bad_set_ups_abort_with_a_message():
    df = two_groups()
    cases = [
        ([None], OPTS, "first input"),
        ([df], {"fieldToPredict": None}, "Field to predict"),
        ([df], {"fieldToPredict": "nope"}, "nope"),
        ([df], {"fieldToPredict": "cls", "useAllNumericFields": False, "fieldsToUse": None}, "Fields to predict from"),
        ([df], {"fieldToPredict": "cls", "useAllNumericFields": False, "fieldsToUse": ["cls"]}, "other than"),
        ([df.assign(t="x")], {"fieldToPredict": "cls", "useAllNumericFields": False, "fieldsToUse": ["t"]},
         "Only numeric"),
        ([df[["cls"]]], {"fieldToPredict": "cls"}, "no numeric fields"),
        ([df.assign(cls="A")], {"fieldToPredict": "cls"}, "at least two"),
        ([df.iloc[:0]], {"fieldToPredict": "cls"}, "No record"),
        ([df, df[["id", "small"]]], {"fieldToPredict": "cls"}, "big"),
    ]
    for inputs, opts, words in cases:
        res = run_block(HERE, inputs, opts)
        assert res.status == "aborted", (opts, res.error)
        assert words in res.final_message, (words, res.final_message)


def test_larger_input():
    train = two_groups(n=5_000, seed=1, scale_big=1.0)
    new = two_groups(n=50_000, seed=2, scale_big=1.0)
    t0 = time.time()
    opts = {"fieldToPredict": "cls", "useAllNumericFields": False, "fieldsToUse": ["small", "big"]}
    out = run_block(HERE, [train, new.drop(columns="cls")], opts).raise_for_error().output(0)
    assert time.time() - t0 < 60
    assert len(out) == 50_000 and (out["Prediction"] == new["cls"]).mean() > 0.95


def test_sample_pump_with_no_vibration_reading_predicted_from_the_other_three():
    opts = {"fieldToPredict": "Condition", "useAllNumericFields": False,
            "fieldsToUse": ["Temperature", "Pressure", "Runtime Hours"]}
    out = run_block(HERE, [HISTORY, READINGS], opts).raise_for_error().output(0)
    assert out.loc[out["Pump"] == "P-2008", "Prediction"].tolist() == ["Worn"]  # as the engineer found


def test_true_false_field_to_predict():
    df = two_groups(scale_big=1.0)
    df["flag"] = df["cls"] == "B"
    new = two_groups(n=10, seed=4, scale_big=1.0)
    new.loc[0, "small"] = None
    opts = {"fieldToPredict": "flag", "useAllNumericFields": False, "fieldsToUse": ["small", "big"]}
    out = run_block(HERE, [df, new], opts).raise_for_error().output(0)
    assert pd.isna(out.loc[0, "Prediction"])
    assert out["Prediction"].iloc[1:].tolist() == (new["cls"].iloc[1:] == "B").tolist()
