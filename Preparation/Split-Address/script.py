"""Split Address: splits a street address ("Baker Street 221B", "221B Baker Street", "Kerkstraat 12-II") into the
street name, the house number and a suffix (the letter or text after the number).

The address must hold the street and number only: no flat or building name before it, no town or postcode after it.
Addresses that fit none of the patterns below get empty street, number and suffix fields.
"""
import re

import pandas as pd
from omniscope.api import OmniscopeApi

L = r"[^\W\d_]"  # a letter, in any alphabet (ß, é, ł ...)

# Tried in this order; each gives (street, rest), where rest starts with the house number.
PATTERNS = [
    (re.compile(rf"^(.+{L}{{2,}}),\s*(\d+.*)$"), (1, 2)),               # Baker Street, 221 B
    (re.compile(r"^(\d+.*),\s*(\D+)$"), (2, 1)),                         # 221 B, Baker Street
    (re.compile(rf"^(.+{L}{{2,}})[\s,.\-]+(\d+.*)$"), (1, 2)),          # Baker Street 221B / Straße des 17. Juni 135
    (re.compile(r"^[^\d@]+$"), (0, None)),                               # Baker Street (no number)
    (re.compile(rf"^((?:{L}|[\s.'])+)(\d+.*)$"), (1, 2)),               # Baker Street221
    (re.compile(rf"^(\d+{L}*),\s*(.*)$"), (2, 1)),                       # 12, Avenue 5 de Mayo
    (re.compile(rf"^(\d+{L}?)\s+(.*{L})$"), (2, 1)),                     # 221 Baker Street / 221B Baker Street
]
NUMBER = re.compile(r"^(\d+)[\s\-./,]*(.*)$")


def split_street(address):
    """(street, rest) for one address, or ('', '') when no pattern fits."""
    for pattern, (street, rest) in PATTERNS:
        match = pattern.search(address)
        if match:
            return match.group(street), (match.group(rest) if rest else "")
    return "", ""


def split_number(rest):
    """(number, suffix) from the part after the street name."""
    match = NUMBER.search(rest)
    if match:
        return match.group(1), match.group(2)
    return "", ""


def split_address(value):
    """(street, number, suffix); missing parts are None."""
    if value is None or pd.isna(value):
        return None, None, None
    address = str(value).strip().strip(",").strip()
    street, rest = split_street(address)
    number, suffix = split_number(rest)
    return street.strip() or None, number or None, suffix.strip() or None


omniscope_api = OmniscopeApi()

address_field = omniscope_api.get_option("address")
street_field = (omniscope_api.get_option("streetname") or "").strip() or "Streetname"
number_field = (omniscope_api.get_option("streetnumber") or "").strip() or "Streetnumber"
suffix_field = (omniscope_api.get_option("suffix") or "").strip() or "Suffix"

if not address_field:
    omniscope_api.abort("Choose the address field.")
if len({street_field, number_field, suffix_field}) < 3:
    omniscope_api.abort("The street name, number and suffix fields need three different names.")

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the addresses to the block's input.")
if address_field not in df.columns:
    omniscope_api.abort(f"The field '{address_field}' is not in the input.")

# each distinct address is split once
addresses = df[address_field]
parts = {v: split_address(v) for v in pd.unique(addresses.dropna())}
split = [parts.get(v, (None, None, None)) if not pd.isna(v) else (None, None, None) for v in addresses]
for i, name in enumerate([street_field, number_field, suffix_field]):
    df[name] = pd.Series([p[i] for p in split], index=df.index, dtype=object)

unrecognised = int((addresses.notna() & df[street_field].isna()).sum())
if unrecognised:
    omniscope_api.update_message(f"{unrecognised} of {int(addresses.notna().sum())} addresses not recognised: "
                                 "their street name, number and suffix are empty.")

omniscope_api.write_output_records(df, output_number=0)
omniscope_api.close()
