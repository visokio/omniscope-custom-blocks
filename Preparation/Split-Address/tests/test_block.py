import os
import time

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "delivery-addresses.csv")
FIELDS = ["Streetname", "Streetnumber", "Suffix"]


def split(addresses, **options):
    df = pd.DataFrame({"a": addresses})
    res = run_block(HERE, df, {"address": "a", **options}).raise_for_error()
    out = res.output(0)
    return [tuple(None if pd.isna(v) else v for v in row) for row in out[FIELDS].itertuples(index=False)], res


def test_sample_addresses():
    res = run_block(HERE, SAMPLE, {"address": "Address"}).raise_for_error()
    out = res.output(0)
    assert len(out) == 16
    assert list(out.columns) == ["Customer", "Address", "Town", "Country"] + FIELDS
    got = {c: tuple(None if pd.isna(v) else v for v in row)
           for c, row in zip(out["Customer"], out[FIELDS].itertuples(index=False))}
    assert got["K-1001"] == ("Kerkstraat", "12", "A")
    assert got["K-1002"] == ("Prinsengracht", "263", "1")
    assert got["K-1003"] == ("Hauptstraße", "5", None)
    assert got["K-1004"] == ("Lindenallee", "17", "b")
    assert got["K-1005"] == ("Baker Street", "221", "B")
    assert got["K-1006"] == ("Mill Lane", "14", None)
    assert got["K-1007"] == ("Rue de l'Église", "4", None)
    assert got["K-1008"] == ("rue des Lilas", "8", None)
    assert got["K-1010"] == ("Molenweg", "7", "bis")
    assert got["K-1012"] == ("Bredgade", "40", "2. tv")
    assert got["K-1013"] == (None, None, None)          # a number range is not recognised
    assert got["K-1014"] == (None, None, None)          # missing address
    assert got["K-1015"] == ("Station Road", None, None)
    assert got["K-1016"] == ("Straße des 17. Juni", "135", None)
    assert out["Streetname"].notna().sum() == 14
    assert res.messages == ["1 of 15 addresses not recognised: their street name, number and suffix are empty."]


@pytest.mark.parametrize("address,expected", [
    # the examples the block has always promised
    ("Baker Street 221B", ("Baker Street", "221", "B")),
    ("Baker Street 221 B", ("Baker Street", "221", "B")),
    ("Baker Street 221-B", ("Baker Street", "221", "B")),
    ("Baker Street, 221 B", ("Baker Street", "221", "B")),
    ("Baker Street 221 Apt B", ("Baker Street", "221", "Apt B")),
    ("221B, Baker Street", ("Baker Street", "221", "B")),
    ("221 B, Baker Street", ("Baker Street", "221", "B")),
    ("221 Apt B, Baker Street", ("Baker Street", "221", "Apt B")),
    ("221 Baker Street", ("Baker Street", "221", None)),
    ("12 rue de la Paix", ("rue de la Paix", "12", None)),
    ("1600 Pennsylvania Avenue NW", ("Pennsylvania Avenue NW", "1600", None)),
    ("Kerkstraat 12-II", ("Kerkstraat", "12", "II")),
    ("Avenida 5 de Mayo 22", ("Avenida 5 de Mayo", "22", None)),
    ("  Baker Street 221B , ", ("Baker Street", "221", "B")),
])
def test_supported_formats(address, expected):
    assert split([address])[0] == [expected]


def test_number_with_a_letter_before_the_street():
    # The original left "221B Baker Street" (no comma) empty
    assert split(["221B Baker Street", "12a High Street"])[0] == [("Baker Street", "221", "B"),
                                                                  ("High Street", "12", "a")]


def test_street_names_ending_in_other_alphabets():
    # The original only knew a-z, so a street ending in ß, é or ø was not recognised
    assert split(["Hauptstraße 5", "Allée 3", "Kongensgade 7", "Søndergårdsvej 9"])[0] == [
        ("Hauptstraße", "5", None), ("Allée", "3", None), ("Kongensgade", "7", None), ("Søndergårdsvej", "9", None)]


@pytest.mark.parametrize("address,expected", [
    ("Flat 3, 12 High Street", ("Flat", "3", "12 High Street")),     # flat before the number
    ("Unit 5 Riverside Park", ("Unit", "5", "Riverside Park")),
    ("Baker Street 221B, London", ("Baker Street", "221", "B, London")),  # town after the number
    ("221 Baker Street, London NW1 6XE", ("Baker Street, London NW1 6XE", "221", None)),
    ("Laan 1940-1945 10", ("Laan", "1940", "1945 10")),           # a street name ending in numbers
    ("PO Box 123", ("PO Box", "123", None)),
    ("12-14 Market Place", (None, None, None)),                    # a number range
])
def test_known_limits(address, expected):
    """Formats the block does not handle; these results are documented in the README."""
    assert split([address])[0] == [expected]


def test_missing_values_and_empty_input():
    # The original stopped with "'float' object has no attribute 'strip'" on a missing address (pandas 3),
    # or gave the street name "nan" (pandas 2); and failed with "not enough values to unpack" on empty input
    rows, res = split(["Kerkstraat 1", None])
    assert rows == [("Kerkstraat", "1", None), (None, None, None)] and res.messages == []
    df = pd.DataFrame({"a": pd.Series([], dtype=object), "n": pd.Series([], dtype="int64")})
    out = run_block(HERE, df, {"address": "a"}).raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["a", "n"] + FIELDS


def test_new_field_names():
    df = pd.DataFrame({"a": ["Kerkstraat 12A"]})
    opts = {"address": "a", "streetname": "Street", "streetnumber": "No", "suffix": "Addition"}
    out = run_block(HERE, df, opts).raise_for_error().output(0)
    assert out.iloc[0][["Street", "No", "Addition"]].tolist() == ["Kerkstraat", "12", "A"]
    out = run_block(HERE, df, {"address": "a", "streetname": " ", "suffix": None}).raise_for_error().output(0)
    assert list(out.columns) == ["a"] + FIELDS  # blank names fall back to the defaults
    res = run_block(HERE, df, {"address": "a", "streetname": "X", "streetnumber": "X"})
    assert res.status == "aborted" and "three different names" in res.final_message


def test_bad_options_and_no_input():
    df = pd.DataFrame({"a": ["Kerkstraat 1"]})
    res = run_block(HERE, df, {"address": None})
    assert res.status == "aborted" and "Choose the address field" in res.final_message
    res = run_block(HERE, df, {"address": "gone"})
    assert res.status == "aborted" and "not in the input" in res.final_message
    res = run_block(HERE, None, {"address": "a"})
    assert res.status == "aborted" and "Connect" in res.final_message


def test_large_input_is_fast():
    n = 200_000
    streets = ["Kerkstraat", "Baker Street", "Hauptstraße", "Mill Lane"]
    df = pd.DataFrame({"id": range(n), "a": [f"{streets[i % 4]} {i % 997 + 1}{'AB'[i % 2]}" for i in range(n)]})
    t0 = time.time()
    out = run_block(HERE, df, {"address": "a"}).raise_for_error().output(0)
    assert time.time() - t0 < 30
    assert len(out) == n and out["Streetname"].notna().all()
    assert out.iloc[5][FIELDS].tolist() == ["Baker Street", "6", "B"]
