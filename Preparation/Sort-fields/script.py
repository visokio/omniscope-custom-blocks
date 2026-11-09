import re

import pandas as pd
from omniscope.api import OmniscopeApi

# Initialize Omniscope API
omniscope_api = OmniscopeApi()

# Order of the type groups when sorting by type
TYPE_ORDER = ["Text", "Number", "Date", "Boolean", "Other"]


def type_group(dtype):
    """Omniscope type group of a field. Integer and Decimal are one group, so that a chunk in which an
    integer field happens to be all missing (and arrives as decimal) sorts the same as the others."""
    if pd.api.types.is_bool_dtype(dtype):
        return "Boolean"
    if pd.api.types.is_numeric_dtype(dtype):
        return "Number"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "Date"
    if pd.api.types.is_string_dtype(dtype) or pd.api.types.is_object_dtype(dtype):
        return "Text"
    return "Other"


def natural_key(name):
    """Case-insensitive, with numbers in names compared by value: Q2 before Q10, apple before Banana."""
    parts = re.split(r"(\d+)", str(name).casefold())
    return [(0, int(p), p) if p.isdigit() else (1, 0, p) for p in parts], str(name)


def sort_dataframe_columns(df, sort_by, first_fields):
    first = [c for c in first_fields if c in df.columns]
    rest = [c for c in df.columns if c not in first]
    if sort_by == 'name':
        rest = sorted(rest, key=natural_key)
    elif sort_by == 'type':
        rest = sorted(rest, key=lambda c: (TYPE_ORDER.index(type_group(df[c].dtype)), natural_key(c)))
    return df[first + rest]


# Fetch the options
sort_by_option = omniscope_api.get_option('sortBy') or 'name'
if sort_by_option not in ('name', 'type'):
    omniscope_api.abort(f"'Sort fields by' must be Name or Type, not {sort_by_option}")
first_fields = omniscope_api.get_option('firstFields') or []

# Sort the fields of each chunk of the data stream
omniscope_api.process_stream(lambda data: sort_dataframe_columns(data, sort_by_option, first_fields))

# Close the API after processing is complete
omniscope_api.close()
