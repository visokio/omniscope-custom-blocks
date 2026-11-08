import os
import random
import time

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
DATA = os.path.join(HERE, "sample-data")
CRM = os.path.join(DATA, "crm-accounts.csv")
INVOICES = os.path.join(DATA, "invoices-to-match.csv")
SUPPLIERS = os.path.join(DATA, "supplier-master.csv")


def run(inputs, **opts):
    return run_block(HERE, inputs, opts)


def test_dedupe_groups_known_duplicates():
    res = run(CRM, match_field="Company", block_field="Postcode").raise_for_error()
    out = res.output(0).set_index("Account ID")
    assert len(out) == 40
    acme = out.loc[["A001", "A002", "A003"], "Group ID"]
    assert acme.nunique() == 1
    assert out.loc["A001", "Is Group Master"] == "Yes" and out.loc["A002", "Is Group Master"] == "No"
    assert out.loc["A001", "Group Size"] == 3
    # different postcode: not compared when blocking on postcode
    assert out.loc["A040", "Group ID"] != out.loc["A001", "Group ID"]
    # distinct businesses stay apart
    assert out.loc["A006", "Group Size"] == 1
    pairs = res.output(1)
    assert {"Record 1", "Record 2", "Score", "Group ID"} <= set(pairs.columns)
    assert (pairs["Score"] >= 0.88).all()


def test_dedupe_without_blocking_finds_typo_in_other_postcode():
    out = run(CRM, match_field="Company").raise_for_error().output(0).set_index("Account ID")
    assert out.loc["A040", "Group ID"] == out.loc["A001", "Group ID"]


def test_lookup_mode_appends_best_reference_match():
    res = run([INVOICES, SUPPLIERS], match_field="Supplier on Invoice", reference_field="Supplier Name",
              block_field="Postcode", algorithm="TOKEN_SET", threshold=0.85).raise_for_error()
    out = res.output(0).set_index("Invoice")
    assert len(out) == 20  # one row per invoice with max_matches=1
    assert out.loc["INV-5001", "Match: Supplier No"] == "S100"
    assert out.loc["INV-5014", "Match: Supplier No"] == "S113"  # Kingsfisher -> Kingfisher
    assert out.loc["INV-5019", "Match Status"] == "No match"
    assert pd.isna(out.loc["INV-5019", "Match Score"])
    assert out["Match Rank"].dtype == "Int64"


def test_lookup_multiple_matches_per_record():
    res = run([INVOICES, SUPPLIERS], match_field="Supplier on Invoice", reference_field="Supplier Name",
              threshold=0.5, max_matches=3).raise_for_error()
    out = res.output(0)
    assert out.groupby("Invoice").size().max() == 3
    assert set(out["Match Rank"].dropna().astype(int)) <= {1, 2, 3}


@pytest.mark.parametrize("algorithm", ["TOKEN_SORT_JW", "JW", "LEVENSHTEIN", "TOKEN_SET", "TRIGRAM"])
def test_every_algorithm_runs_and_scores_identical_as_one(algorithm):
    df = pd.DataFrame({"Name": ["Blue Oak Ltd", "Blue Oak Limited", "Red River"]})
    res = run(df, match_field="Name", algorithm=algorithm, threshold=0.99).raise_for_error()
    out = res.output(0)
    assert out.loc[0, "Group ID"] == out.loc[1, "Group ID"] != out.loc[2, "Group ID"]


def test_second_field_blends_into_score():
    df = pd.DataFrame({"Name": ["John Smith", "John Smith"], "Street": ["1 High Street", "99 Totally Different Road"]})
    same = run(df, match_field="Name").raise_for_error().output(1)
    blended = run(df, match_field="Name", second_field="Street", second_weight=0.5).raise_for_error().output(1)
    assert len(same) == 1 and len(blended) == 0


def test_empty_input_gives_empty_outputs_with_schema():
    df = pd.DataFrame({"Company": pd.Series([], dtype=object)})
    res = run(df, match_field="Company").raise_for_error()
    assert len(res.output(0)) == 0 and "Group ID" in res.output(0).columns
    assert len(res.output(1)) == 0 and "Score" in res.output(1).columns


def test_wrong_types_numbers_and_nulls_are_handled():
    df = pd.DataFrame({"Code": [12345, 12345, 12354, None, 99]})
    res = run(df, match_field="Code", threshold=0.8).raise_for_error()
    out = res.output(0)
    assert out.loc[0, "Group ID"] == out.loc[1, "Group ID"]
    assert out.loc[3, "Group Size"] == 1  # null never matches


def test_missing_field_aborts_with_clear_message():
    res = run(CRM, match_field="Nope")
    assert res.status == "aborted" and "Nope" in res.final_message


def test_reference_field_missing_in_second_input_aborts():
    res = run([INVOICES, SUPPLIERS], match_field="Supplier on Invoice")
    assert res.status == "aborted" and "second input" in res.final_message


def test_large_input_is_fast_enough():
    random.seed(7)
    words = ["north", "south", "acme", "global", "tech", "foods", "solar", "marine", "print", "design",
             "logistics", "dental", "farm", "hotel", "brew", "stone", "water", "energy", "software", "retail"]
    names = [" ".join(random.sample(words, 3)).title() + " Ltd" for _ in range(6000)]
    df = pd.DataFrame({"Name": names, "Id": range(6000)})
    t0 = time.time()
    res = run(df, match_field="Name", threshold=0.97).raise_for_error()
    assert time.time() - t0 < 60
    assert len(res.output(0)) == 6000
