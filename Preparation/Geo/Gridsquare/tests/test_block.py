import os
import time

import pandas as pd
import pytest

from harness.runner import run_block

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # the block's folder
SAMPLE = os.path.join(HERE, "sample-data", "station-log.csv")


def run(data, **options):
    return run_block(HERE, [data], {"gsfield": "Locator", **options})


def located(locators):
    out = run(pd.DataFrame({"Locator": locators})).raise_for_error().output(0)
    return list(zip(out["Longitude"], out["Latitude"]))


def test_sample():
    res = run(SAMPLE).raise_for_error()
    out = res.output(0)
    assert len(out) == 12
    assert list(out.columns) == ["Station", "Locator", "Contacts", "Longitude", "Latitude"]
    by_station = out.set_index("Station")
    assert (by_station.loc["Harbour club", "Longitude"], by_station.loc["Harbour club", "Latitude"]) == \
        pytest.approx((-0.125, 51.5208333))
    # the invalid locator (IO92ZZ: Z is past X) and the empty one have no coordinates
    assert by_station.loc[["Canal workshop", "Market square"], "Longitude"].isna().all()
    assert out["Longitude"].notna().sum() == 10
    assert res.final_message == "10 of 12 records located; 1 not a valid locator (empty Longitude and Latitude)"
    assert str(out["Longitude"].dtype) == "float64"


def test_every_precision_gives_the_centre_of_its_square():
    got = located(["IO", "IO91", "IO91wm", "IO91wm52", "IO91wm52kx"])
    expected = [(-10.0, 55.0), (-1.0, 51.5), (-0.125, 51.5208333), (-0.1208333, 51.5104167),
                (-0.1213542, 51.5124132)]
    for g, e in zip(got, expected):
        assert g == pytest.approx(e, abs=1e-6)


def test_eight_character_example_from_the_description():
    # the extended square digits (16) count: centre of a 30 x 15 second square, not of the 6-character one
    assert located(["BL11bh16"])[0] == pytest.approx((-157.9041667, 21.31875), abs=1e-6)


def test_corners_of_the_grid():
    got = located(["AA00aa", "RR99xx"])
    assert got[0] == pytest.approx((-179.9583333, -89.9791667), abs=1e-6)
    assert got[1] == pytest.approx((179.9583333, 89.9791667), abs=1e-6)


def test_case_and_spaces_are_ignored():
    got = located(["io91WM", " IO91wm "])
    assert got[0] == pytest.approx((-0.125, 51.5208333)) and got[1] == got[0]


def test_invalid_and_missing_locators_get_empty_coordinates():
    res = run(pd.DataFrame({"Locator": ["ZZ99", "IO9", "IO91w", "IO91wm5", "SA00", "IO91yy", None, "IO91"]}))
    out = res.raise_for_error().output(0)
    assert out["Longitude"].isna().tolist() == [True] * 7 + [False]
    assert "1 of 8 records located; 6 not a valid locator" in res.final_message


def test_existing_fields_with_the_new_names_are_replaced():
    data = pd.DataFrame({"Locator": ["IO91"], "Latitude": ["old"], "Other": [1]})
    out = run(data).raise_for_error().output(0)
    assert list(out.columns) == ["Locator", "Latitude", "Other", "Longitude"]
    assert out["Latitude"][0] == 51.5


def test_custom_field_names():
    out = run(pd.DataFrame({"Locator": ["IO91"]}), lonfield="X", latfield="Y").raise_for_error().output(0)
    assert list(out.columns) == ["Locator", "X", "Y"]


def test_bad_options_abort():
    data = pd.DataFrame({"Locator": ["IO91"]})
    for opts, text in [({"gsfield": None}, "Grid square field"), ({"gsfield": "Nope"}, "no field"),
                       ({"lonfield": ""}, "Give names"), ({"lonfield": "Lat", "latfield": "Lat"}, "different"),
                       ({"lonfield": "Locator"}, "can't also")]:
        res = run_block(HERE, [data], {"gsfield": "Locator", **opts})
        assert res.status == "aborted" and res.error is None, opts
        assert text in res.final_message


def test_no_input_aborts():
    res = run_block(HERE, [], {"gsfield": "Locator"})
    assert res.status == "aborted"


def test_numeric_field_gives_empty_coordinates():
    out = run(pd.DataFrame({"Locator": [1234, 5678]})).raise_for_error().output(0)
    assert out["Longitude"].isna().all()


def test_empty_input():
    out = run(pd.DataFrame({"Locator": pd.Series([], dtype=object), "N": pd.Series([], dtype="Int64")}))
    out = out.raise_for_error().output(0)
    assert len(out) == 0 and list(out.columns) == ["Locator", "N", "Longitude", "Latitude"]


def test_large_input():
    data = pd.DataFrame({"Locator": ["IO91wm", "JO02bf52", "IO83"] * 70000})
    t = time.time()
    out = run(data).raise_for_error().output(0)
    assert len(out) == 210000 and out["Longitude"].notna().all()
    assert time.time() - t < 30
