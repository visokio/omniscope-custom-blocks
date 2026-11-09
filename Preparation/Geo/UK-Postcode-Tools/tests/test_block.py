import os
import time

import numpy as np
import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "customer-addresses.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, {"postcode_field": "pc", **opts})


def test_format_and_split():
    out = run(pd.DataFrame({"pc": ["ls15hd", "SW1V 3QT", "M3  2EG", "ab101ab", "GIR 0AA"]})).raise_for_error().output(0)
    assert out["Postcode Formatted"].tolist() == ["LS1 5HD", "SW1V 3QT", "M3 2EG", "AB10 1AB", "GIR 0AA"]
    r = out.iloc[1]
    assert (r["Postcode Area"], r["Postcode District"], r["Postcode Sector"]) == ("SW", "SW1V", "SW1V 3")
    assert out["Postcode Country"].tolist()[:4] == ["England", "England", "England", "Scotland"]
    assert out["Postcode Valid"].eq("Yes").all()


def test_invalid_reasons_and_letter_o_fix():
    out = run(pd.DataFrame({"pc": ["BS1 4D", "QQ1 1AA", "YO1 OAB", None, "LS1 5CI", "1234567"]})).raise_for_error().output(0)
    assert out["Postcode Problem"].tolist()[0].startswith("Inward")  # "4D" is not a valid inward code
    assert run(pd.DataFrame({"pc": ["AB1"]})).raise_for_error().output(0)["Postcode Problem"].iloc[0] == "Wrong length"
    assert out["Postcode Problem"].tolist()[1] == "Letters or digits not allowed in this position"  # Q cannot start a postcode
    assert out["Postcode Formatted"].tolist()[2] == "YO1 0AB" and out["Postcode Valid"].tolist()[2] == "Yes"
    assert out["Postcode Problem"].tolist()[3] == "Missing"
    assert out["Postcode Valid"].tolist()[4] == "No"


def test_extract_from_address_and_replace():
    df = pd.DataFrame({"pc": ["12 Park Row, Leeds LS1 5HD", "no postcode here", "Flat 3, Deansgate, Manchester m3 2eg"]})
    out = run(df, extract_from_text=True).raise_for_error().output(0)
    f = out["Postcode Formatted"].tolist()
    assert f[0] == "LS1 5HD" and pd.isna(f[1]) and f[2] == "M3 2EG"
    r = run(pd.DataFrame({"pc": ["ls15hd", "bad"]}), replace_field=True, prefix="PC").raise_for_error().output(0)
    assert r["pc"].tolist() == ["LS1 5HD", "bad"] and "PC Valid" in r.columns and "PC Formatted" not in r.columns


def test_sample_summary():
    res = run_block(HERE, SAMPLE, {"postcode_field": "Postcode"}).raise_for_error()
    out, s = res.output(0), res.output(1)
    assert (out["Postcode Valid"] == "Yes").sum() == 21
    assert s["Records"].sum() == 24 and "(invalid)" in set(s["Postcode Country"])
    assert set(out["Postcode Country"].dropna()) >= {"England", "Scotland", "Wales", "Northern Ireland", "Channel Islands", "Isle of Man"}


def test_numbers_empty_and_bad_field():
    out = run(pd.DataFrame({"pc": [12345, np.nan]})).raise_for_error().output(0)
    assert out["Postcode Valid"].tolist() == ["No", "No"]
    assert len(run(pd.DataFrame({"pc": pd.Series([], dtype=object)})).raise_for_error().output(0)) == 0
    assert run(pd.DataFrame({"x": ["LS1 5HD"]})).status == "aborted"


def test_large_input_is_fast():
    df = pd.DataFrame({"pc": ["ls15hd", "SW1V 3QT", "bad", "EH2 2PR"] * 100_000})
    t0 = time.time()
    out = run(df).raise_for_error().output(0)
    assert time.time() - t0 < 60 and (out["Postcode Valid"] == "Yes").sum() == 300_000
