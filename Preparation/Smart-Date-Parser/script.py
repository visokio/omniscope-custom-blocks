import re
from datetime import datetime, timezone

import pandas as pd
from dateutil import parser as dateutil_parser
from omniscope.api import OmniscopeApi

api = OmniscopeApi()

# ============================================================================
# OMNISCOPE CUSTOM BLOCK: Smart Date Parser (Streaming)
# Parses text fields holding dates in mixed formats into Date fields.
# ============================================================================


def opt(name, default):
    """Get option value with fallback to default."""
    v = api.get_option(name)
    return default if v is None or str(v).strip() == "" else v


def flag(name, default):
    """A Boolean option; an unset option takes the default."""
    return str(opt(name, default)).strip().lower() in ("true", "1", "yes", "y")


# Configuration options
fields_to_parse = api.get_option("fields_to_parse")  # a list of field names
output_suffix = api.get_option("output_suffix")  # empty: replace the field in place
# A leading space is kept (" parsed" gives "Order Date parsed"); trailing spaces are dropped
output_suffix = str(output_suffix).rstrip() if output_suffix else ""

prefer_day_first = flag("prefer_day_first", "false")
add_failure_flag = flag("add_failure_flag", "true")
keep_original = flag("keep_original_fields", "true")
custom_formats = str(opt("custom_formats", "")).strip()

if not fields_to_parse:
    api.abort("Choose at least one field to parse in 'Fields to parse'.")

parse_fields = list(fields_to_parse)

# Custom formats are comma-separated Python strptime codes
extra_formats = [f.strip() for f in custom_formats.split(",") if f.strip()] if custom_formats else []

# ============================================================================
# Date Parsing Logic
# ============================================================================

# A value that starts with a four-digit year (2025-03-04, 2025/03/04) is always year-month-day,
# whatever the day-first preference.
YEAR_FIRST = re.compile(r"^\s*\d{4}[-/.]\d{1,2}[-/.]\d{1,2}")

# dateutil fills any part missing from the text (year, month or day) from a default date, which would
# make "March" or "12" a date that depends on the day the workflow runs. Parsing with two different
# defaults shows which parts the text really holds.
DEFAULT_A = datetime(2000, 1, 1)
DEFAULT_B = datetime(2001, 2, 2)


def to_naive_utc(d):
    """Dates with a time zone or offset are converted to UTC; the result has no zone."""
    if d.tzinfo is not None:
        d = d.astimezone(timezone.utc).replace(tzinfo=None)
    return d


def parse_complete(date_str, day_first):
    """dateutil parse that fails unless the text holds a year, a month and a day."""
    a = dateutil_parser.parse(date_str, dayfirst=day_first, default=DEFAULT_A)
    b = dateutil_parser.parse(date_str, dayfirst=day_first, default=DEFAULT_B)
    if (a.year, a.month, a.day) != (b.year, b.month, b.day):
        raise ValueError("incomplete date")
    return a


COMMON_FORMATS = [
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S',
    '%Y/%m/%d',
    '%Y-%m-%d',
    '%m/%d/%Y',
    '%d/%m/%Y',
    '%m-%d-%Y',
    '%d-%m-%Y',
    '%Y/%m/%d %H:%M:%S',
    '%d/%m/%Y %H:%M:%S',
    '%m/%d/%Y %H:%M:%S',
    '%Y%m%d',
    '%d %b %Y',
    '%d %B %Y',
    '%b %d, %Y',
    '%B %d, %Y',
    '%Y-%m-%dT%H:%M:%SZ',
    '%Y-%m-%dT%H:%M:%S',
]


def parse_flexible_date(date_value, day_first=False, extra_fmts=None):
    """
    Attempts to parse a date string using several strategies.
    Returns a datetime (no time zone) or None if parsing fails.
    """
    if date_value is None or (not isinstance(date_value, str) and pd.isna(date_value)):
        return None

    date_str = str(date_value).strip()
    if not date_str:
        return None

    # Strategy 1: the custom formats, in the order given
    for fmt in extra_fmts or []:
        try:
            return to_naive_utc(datetime.strptime(date_str, fmt))
        except (ValueError, TypeError):
            continue

    preferred = False if YEAR_FIRST.match(date_str) else day_first

    # Strategy 2: dateutil with the preferred day-first setting, then the other one as a fallback
    for df in (preferred, not preferred):
        try:
            return to_naive_utc(parse_complete(date_str, df))
        except (ValueError, OverflowError, TypeError):
            pass

    # Strategy 3: explicit common formats
    for fmt in COMMON_FORMATS:
        try:
            return to_naive_utc(datetime.strptime(date_str, fmt))
        except (ValueError, TypeError):
            continue

    return None


def parse_series(values: pd.Series) -> pd.Series:
    """Parse a field; each distinct value is parsed once."""
    if pd.api.types.is_datetime64_any_dtype(values.dtype):
        return values.copy()  # already a Date field
    cache = {}
    out = []
    for v in values:
        key = v if isinstance(v, str) else (None if pd.isna(v) else str(v))
        if key not in cache:
            cache[key] = parse_flexible_date(key, day_first=prefer_day_first, extra_fmts=extra_formats)
        out.append(cache[key])
    return pd.to_datetime(pd.Series(out, index=values.index, dtype=object), errors="coerce").astype("datetime64[us]")


# ============================================================================
# Chunk Processing
# ============================================================================

def handle_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    """Process each chunk of data."""

    # Preserve original column order
    original_columns = list(chunk.columns)
    result = chunk.copy()

    for field in parse_fields:
        if field not in chunk.columns:
            continue

        output_field = field + output_suffix if output_suffix else field  # no suffix: overwrite in place
        if output_field != field and output_field in chunk.columns:
            api.abort(f"The input already has a field called '{output_field}'. Change 'Output suffix'.")

        parsed_values = parse_series(chunk[field])

        if output_field == field:
            result[field] = parsed_values
        else:
            # Add the new field right after the original one
            original_columns.insert(original_columns.index(field) + 1, output_field)
            result[output_field] = parsed_values

        if add_failure_flag:
            flag_field = output_field + "_failed"
            if flag_field in chunk.columns:
                api.abort(f"The input already has a field called '{flag_field}'. Change 'Output suffix'.")
            flag_values = parsed_values.isna() & chunk[field].notna()
            original_columns.insert(original_columns.index(output_field) + 1, flag_field)
            result[flag_field] = flag_values.astype(bool)

    # Drop original fields if requested and we're using a suffix
    if not keep_original and output_suffix:
        fields_to_drop = [f for f in parse_fields if f in result.columns]
        result = result.drop(columns=fields_to_drop)
        original_columns = [c for c in original_columns if c not in fields_to_drop]

    # Return with preserved column order
    return result[original_columns]

# ============================================================================
# Execute Streaming Processing
# ============================================================================


api.process_stream(handle_chunk)

# the data stream is over. No other data can be read or written.
api.close()
