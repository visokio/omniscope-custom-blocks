import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "telecom-customers.csv")
P = ["Tenure Months", "Contract", "Broadband", "Lines", "Support Calls (last 90 days)"]


def run(df, **opts):
    return run_block(HERE, df, opts)


def test_exact_linear_fit():
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6], "g": ["a", "b", "a", "b", "a", "b"]})
    df["y"] = 2 + 3 * df["x"] + np.where(df["g"] == "b", 10, 0)
    res = run(df, target_field="y", predictor_fields=["x", "g"]).raise_for_error()
    c = res.output(0).set_index("Term")
    assert np.isclose(c.loc["(Intercept)", "Coefficient"], 2) and np.isclose(c.loc["x", "Coefficient"], 3)
    assert np.isclose(c.loc["g = b", "Coefficient"], 10) or np.isclose(c.loc["g = a", "Coefficient"], -10)
    f = res.output(1).set_index("Statistic")["Value"]
    assert np.isclose(f["R-squared"], 1.0)
    assert np.allclose(res.output(2)["Residual"], 0, atol=1e-9)


def test_linear_matches_statsmodels_on_sample():
    res = run(SAMPLE, target_field="Monthly Spend", predictor_fields=P).raise_for_error()
    c = res.output(0).set_index("Term")
    # reference values from statsmodels 0.15 OLS on the same data
    assert np.isclose(c.loc["(Intercept)", "Coefficient"], 31.3485, atol=1e-4) and np.isclose(c.loc["Lines", "Std Error"], 0.1376, atol=1e-4)
    assert np.isclose(c.loc["Broadband = Copper", "Coefficient"], -14.153, atol=1e-3) and np.isclose(c.loc["Contract = Two year", "Std Error"], 0.4101, atol=1e-4)
    f = res.output(1).set_index("Statistic")["Value"]
    assert np.isclose(f["R-squared"], 0.8262202638854501) and np.isclose(f["F statistic"], 1173.5470795511064) and np.isclose(f["AIC"], 9550.764056675907)
    assert f["Rows left out (missing values)"] == 12
    s = res.output(2)
    assert s["Prediction"].notna().sum() == 1500 and s["Residual"].notna().sum() == 1488  # rows with missing target still scored
    assert (s["Prediction Low"] < s["Prediction"]).all()


def test_logistic_matches_statsmodels_on_sample():
    res = run(SAMPLE, target_field="Churned", predictor_fields=P + ["Monthly Spend"]).raise_for_error()
    c = res.output(0).set_index("Term")
    assert np.isclose(c.loc["Tenure Months", "Coefficient"], -0.0359, atol=1e-4) and np.isclose(c.loc["Contract = Two year", "Std Error"], 0.2955, atol=1e-4)
    assert np.isclose(c.loc["Support Calls (last 90 days)", "Odds Ratio"], np.exp(0.4385), rtol=1e-3)
    f = res.output(1).set_index("Statistic")
    assert np.isclose(f.loc["Log-likelihood", "Value"], -610.9845439342137) and np.isclose(f.loc["McFadden pseudo R-squared", "Value"], 0.1626517240085099)
    assert np.isclose(f.loc["Likelihood-ratio p-value", "Value"], 1.351631398568621e-47, rtol=1e-6) and f.loc["Positive class", "Text"] == "Yes"
    s = res.output(2)
    assert s["Probability"].between(0, 1).sum() == 1488 and set(s["Predicted Class"].dropna()) <= {"Yes", "Not Yes"}


def test_vif_collinearity_and_errors():
    rng = np.random.default_rng(0)
    x = rng.normal(size=200)
    df = pd.DataFrame({"x1": x, "x2": x + rng.normal(0, 0.01, 200), "x3": rng.normal(size=200)})
    df["y"] = df["x1"] + df["x3"] + rng.normal(size=200)
    res = run(df, target_field="y", predictor_fields=["x1", "x2", "x3"]).raise_for_error()
    v = res.output(0).set_index("Term")["VIF"]
    assert v["x1"] > 100 and v["x3"] < 2 and "VIF > 10" in res.final_message
    assert run(df.assign(x4=df["x1"] * 2), target_field="y", predictor_fields=["x1", "x4"]).status == "aborted"
    assert run(df, target_field="y", predictor_fields=["y"]).status == "aborted"
    assert run(df, target_field="zz", predictor_fields=["x1"]).status == "aborted"
    assert run(df, target_field="y", predictor_fields=[]).status == "aborted"
    assert run(df.head(2), target_field="y", predictor_fields=["x1", "x3"]).status == "aborted"
    assert run(df.assign(y=["a", "b", "c", "d"] * 50), target_field="y", predictor_fields=["x1"], model="LOGISTIC").status == "aborted"
    assert run(df.iloc[0:0], target_field="y", predictor_fields=["x1"]).status == "aborted"


def test_positive_class_threshold_and_separation():
    rng = np.random.default_rng(2)
    x = rng.normal(size=400)
    y = np.where(rng.random(400) < 1 / (1 + np.exp(-2 * x)), "won", "lost")
    df = pd.DataFrame({"x": x, "y": y})
    a = run(df, target_field="y", predictor_fields=["x"], positive_class="won").raise_for_error()
    b = run(df, target_field="y", predictor_fields=["x"], positive_class="lost").raise_for_error()
    ca, cb = a.output(0).set_index("Term"), b.output(0).set_index("Term")
    assert np.isclose(ca.loc["x", "Coefficient"], -cb.loc["x", "Coefficient"])  # flipping the class flips the sign
    assert run(df, target_field="y", predictor_fields=["x"], positive_class="nope").status == "aborted"
    sep = pd.DataFrame({"x": np.arange(40.0), "y": [0] * 20 + [1] * 20})
    s = run(sep, target_field="y", predictor_fields=["x"]).raise_for_error()
    assert "Warning" in set(s.output(1)["Statistic"])


def test_large_input_is_fast():
    rng = np.random.default_rng(0)
    n = 300_000
    df = pd.DataFrame({f"x{i}": rng.normal(size=n) for i in range(10)})
    df["cat"] = rng.choice(list("abcdefgh"), n)
    df["y"] = df.sum(axis=1, numeric_only=True) + rng.normal(size=n)
    df["b"] = np.where(df["y"] > 0, "Yes", "No")
    t0 = time.time()
    run(df, target_field="y", predictor_fields=[f"x{i}" for i in range(10)] + ["cat"]).raise_for_error()
    run(df, target_field="b", predictor_fields=[f"x{i}" for i in range(10)] + ["cat"]).raise_for_error()
    assert time.time() - t0 < 120
