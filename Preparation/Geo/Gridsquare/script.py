import re

import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

# Maidenhead locator pairs, largest first: (characters allowed, number of steps, longitude size, latitude size).
# A field is 20 x 10 degrees, a square 2 x 1, a subsquare 5 x 2.5 minutes, an extended square 30 x 15 seconds,
# an extended subsquare 1.25 x 0.625 seconds.
PAIRS = [
    ("A-R", 18, 20.0, 10.0),
    ("0-9", 10, 2.0, 1.0),
    ("A-X", 24, 2.0 / 24, 1.0 / 24),
    ("0-9", 10, 2.0 / 240, 1.0 / 240),
    ("A-X", 24, 2.0 / 5760, 1.0 / 5760),
]
LOCATOR = re.compile(r"[A-R]{2}(?:[0-9]{2}(?:[A-X]{2}(?:[0-9]{2}(?:[A-X]{2})?)?)?)?")


def step(ch):
    return int(ch) if ch.isdigit() else ord(ch) - ord("A")


def centre(locator):
    """(longitude, latitude) of the centre of the square a locator names, or None if it is not a locator."""
    if not isinstance(locator, str):
        return None
    code = locator.strip().upper()
    if not LOCATOR.fullmatch(code):
        return None
    lon, lat = -180.0, -90.0
    for i in range(0, len(code), 2):
        _, _, lon_size, lat_size = PAIRS[i // 2]
        lon += step(code[i]) * lon_size
        lat += step(code[i + 1]) * lat_size
    _, _, lon_size, lat_size = PAIRS[len(code) // 2 - 1]
    return lon + lon_size / 2, lat + lat_size / 2


input_data = omniscope_api.read_input_records(input_number=0)
if input_data is None:
    omniscope_api.abort("Connect the records with grid square locators to the block's input.")

gs_field = omniscope_api.get_option("gsfield")
lon_field = (omniscope_api.get_option("lonfield") or "").strip()
lat_field = (omniscope_api.get_option("latfield") or "").strip()

if not gs_field:
    omniscope_api.abort("Choose the field with the grid square locators in \"Grid square field\".")
if gs_field not in input_data.columns:
    omniscope_api.abort(f"The input has no field called \"{gs_field}\".")
if not lon_field or not lat_field:
    omniscope_api.abort("Give names for the longitude and latitude fields to create.")
if lon_field == lat_field:
    omniscope_api.abort("The longitude and latitude fields need different names.")
if gs_field in (lon_field, lat_field):
    omniscope_api.abort(f"\"{gs_field}\" holds the locators, so it can't also be a longitude or latitude field name.")

points = [centre(v) for v in input_data[gs_field]]
present = input_data[gs_field].notna() & (input_data[gs_field].astype(str).str.strip() != "")
invalid = sum(1 for p, has in zip(points, present) if p is None and has)

# An existing field with one of the new names is replaced (keeping its position)
output_data = input_data.copy()
output_data[lon_field] = pd.Series([p[0] if p else None for p in points], index=output_data.index, dtype="float64")
output_data[lat_field] = pd.Series([p[1] if p else None for p in points], index=output_data.index, dtype="float64")

message = f"{len(points) - points.count(None)} of {len(points)} records located"
if invalid:
    message += f"; {invalid} not a valid locator (empty {lon_field} and {lat_field})"

omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close(message)
