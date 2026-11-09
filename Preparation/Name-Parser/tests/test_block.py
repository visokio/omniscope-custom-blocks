import os
import time

import pandas as pd

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "contacts.csv")


def parse(*names, **opts):
    res = run_block(HERE, pd.DataFrame({"n": list(names)}), {"name_field": "n", **opts}).raise_for_error()
    return res.output(0)


def test_titles_suffixes_particles_and_case():
    r = parse("dr amelia j. smith-jones", "Ms Freya VAN DER BERG", "Prof. Sir Robert Mcdonald OBE", "mr patrick o'brien").set_index("n")
    a = r.loc["dr amelia j. smith-jones"]
    assert (a["Title"], a["First Name"], a["Middle Names"], a["Last Name"]) == ("Dr", "Amelia", "J", "Smith-Jones")
    assert r.loc["Ms Freya VAN DER BERG", "Last Name"] == "van der Berg"
    k = r.loc["Prof. Sir Robert Mcdonald OBE"]
    assert k["Title"] == "Prof Sir" and k["Suffix"] == "OBE" and k["Last Name"] == "McDonald" and k["Salutation"] == "Dear Sir Robert"
    assert r.loc["mr patrick o'brien", "Salutation"] == "Dear Mr O'Brien"


def test_last_first_initials_orgs_and_edge_cases():
    r = parse("SMITH, JOHN", "Williams Jr, David", "A. B. Patel", "Northbridge Packaging Ltd", "Chloe", "Mrs Taylor", None, "Sam Rivers").reset_index(drop=True)
    assert (r.loc[0, "First Name"], r.loc[0, "Last Name"]) == ("John", "Smith") and "Last, First" in r.loc[0, "Parse Note"]
    assert (r.loc[1, "First Name"], r.loc[1, "Last Name"], r.loc[1, "Suffix"]) == ("David", "Williams", "Jr")
    assert r.loc[2, "First Name"] == "A" and "initial" in r.loc[2, "Parse Note"]
    assert r.loc[3, "Name Type"] == "Organisation" and r.loc[3, "Salutation"] == "Dear Sir or Madam" and pd.isna(r.loc[3, "Initials"])
    assert r.loc[4, "Parse Note"] == "Single word" and r.loc[5, "Salutation"] == "Dear Mrs Taylor" and r.loc[6, "Name Type"] == "Empty"
    assert pd.isna(r.loc[7, "Parse Note"])  # Sam is not an initial


def test_options():
    r = parse("dr amelia smith", fix_case=False, salutation_style="INFORMAL", greeting="Hello", prefix="Contact ")
    assert r["Contact First Name"].iloc[0] == "amelia" and r["Contact Salutation"].iloc[0] == "Hello amelia"


def test_sample_and_bad_inputs():
    r = run_block(HERE, SAMPLE, {"name_field": "Full Name"}).raise_for_error().output(0)
    assert (r["Name Type"] == "Organisation").sum() == 2 and (r["Name Type"] == "Empty").sum() == 1
    assert run_block(HERE, SAMPLE, {"name_field": "zz"}).status == "aborted"
    big = pd.DataFrame({"n": ["Dr Amelia J. Smith-Jones", "SMITH, JOHN", "mr o'brien"] * 40_000})
    t0 = time.time()
    run_block(HERE, big, {"name_field": "n"}).raise_for_error()
    assert time.time() - t0 < 120
