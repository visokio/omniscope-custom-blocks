import re

import pandas as pd
from omniscope.api import OmniscopeApi

api = OmniscopeApi()


def opt(name, default):
    v = api.get_option(name)
    return default if v is None or str(v).strip() == "" else v


def flag(name, default):
    return str(opt(name, default)).strip().lower() in ("true", "1", "yes", "y")


prefer_non_empty = flag("prefer_non_empty_strings", "true")
sort_columns = flag("sort_columns", "false")
day_first = flag("day_first", "false")

try:
    threshold = float(opt("auto_cast_threshold", 0.98))
except (TypeError, ValueError):
    threshold = 0.98
if not 0 < threshold <= 1:
    api.abort("'Auto cast threshold' must be more than 0 and at most 1 (for example 0.98).")

# Defaults for missing values. Unset (the default): missing values stay missing.
dt_default_raw = opt("datetime_default", None)
num_default = opt("number_default", None)
str_default = opt("string_default", None)

dt_default = None
if dt_default_raw is not None:
    dt_default = pd.to_datetime(str(dt_default_raw), errors="coerce")
    if pd.isna(dt_default):
        api.abort(f"'Datetime default' is not a date: {dt_default_raw}. Use a date such as 1970-01-01.")
    if dt_default.tzinfo is not None:
        dt_default = dt_default.tz_convert("UTC").tz_localize(None)
if num_default is not None:
    try:
        num_default = float(num_default)
    except (TypeError, ValueError):
        api.abort(f"'Number default' is not a number: {num_default}")

TRUE_WORDS = ["true", "t", "1", "yes", "y"]
BOOL_WORDS = TRUE_WORDS + ["false", "f", "0", "no", "n"]
# A whole number written with a leading zero (an ID or a postcode such as 00123) stays text
LEADING_ZERO = re.compile(r"^[+-]?0\d")
YEAR_FIRST = re.compile(r"^\s*\d{4}[-/.]")
# Text only counts as a date if it looks like one: 2024-03-02, 04/03/2024, 4 March 2024 or March 4, 2024.
# pandas would otherwise read "March" as 1 March in year 1, and "00123" as the year 123.
DATE_LIKE = re.compile(r"^\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}"
                       r"|\d{1,2}\s+[A-Za-z]{3,}\.?,?\s+\d{4}|[A-Za-z]{3,}\.?\s+\d{1,2},?\s+\d{4})")


def norm(name: str) -> str:
    s = "" if name is None else str(name).strip().lower()
    s = s.replace("-", "_")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s


def is_text(s: pd.Series) -> bool:
    return pd.api.types.is_string_dtype(s.dtype) or pd.api.types.is_object_dtype(s.dtype)


def is_empty(s: pd.Series) -> pd.Series:
    """Missing, or text that is empty after trimming."""
    return s.isna() | s.map(lambda v: isinstance(v, str) and v.strip() == "")


def coalesce_cols(df: pd.DataFrame, cols: list) -> pd.Series:
    """The first field's value, or the next field's where it is missing (or empty, with prefer_non_empty)."""
    out = df[cols[0]]
    if len({str(df[c].dtype) for c in cols}) > 1:
        out = out.astype(object)
    for c in cols[1:]:
        nxt = df[c]
        gap = is_empty(out) if prefer_non_empty else out.isna()
        out = out.where(~gap, nxt)
    return out


def with_default(s: pd.Series, default):
    return s if default is None else s.fillna(default)


def to_number(s: pd.Series) -> pd.Series:
    """Text read as numbers (float); empty and unreadable values are missing."""
    out = pd.to_numeric(s.map(lambda v: v.strip() if isinstance(v, str) else v), errors="coerce")
    return out.astype("float64").where(~is_empty(s))


def to_date(s: pd.Series) -> pd.Series:
    """Text read as dates (naive, UTC); values that don't look like dates are missing."""
    present = ~is_empty(s)
    text = s[present].astype(str).str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[us, UTC]")
    if len(text):
        text = text[text.str.match(DATE_LIKE)]
        # Values starting with a four-digit year are year-month-day whatever the day-first setting
        year_first = text.str.match(YEAR_FIRST)
        dt = pd.concat([
            pd.to_datetime(text[year_first], errors="coerce", format="mixed", utc=True),
            pd.to_datetime(text[~year_first], errors="coerce", format="mixed", dayfirst=day_first, utc=True),
        ])
        if len(dt):
            out[dt.index] = dt.astype("datetime64[us, UTC]")
    return out.dt.tz_localize(None)


def to_bool(s: pd.Series) -> pd.Series:
    """Yes/no words read as a nullable boolean; anything else is missing."""
    lower = s.map(lambda v: v.strip().lower() if isinstance(v, str) else v)
    out = pd.Series(pd.NA, index=s.index, dtype="boolean")
    known = lower[lower.isin(BOOL_WORDS)]
    out[known.index] = known.isin(TRUE_WORDS)
    return out


def choose_type(s: pd.Series) -> str:
    """The type of a text field, from the values present in the first chunk."""
    present = s[~is_empty(s)]
    if len(present) == 0:
        return "text"  # nothing to judge the type by
    text = present.astype(str).str.strip()
    needed = threshold * len(present)
    num = pd.to_numeric(text, errors="coerce")
    if num.notna().sum() >= needed and not text.str.match(LEADING_ZERO).any():
        whole = num.dropna()
        if (len(whole) and (whole == whole.round()).all() and whole.abs().max() < 2 ** 53
                and (num_default is None or num_default == int(num_default))):
            return "integer"
        return "decimal"
    if text.str.match(DATE_LIKE).sum() >= needed and to_date(present).notna().sum() >= needed:
        return "date"
    if text.str.lower().isin(BOOL_WORDS).sum() >= needed:
        return "boolean"
    return "text"


def cast(s: pd.Series, kind: str):
    """Convert one chunk's values to the field's chosen type. Returns the values and how many didn't fit."""
    if kind == "text":
        return with_default(s.astype(object).where(~s.isna(), None), str_default), 0
    out = {"integer": to_number, "decimal": to_number, "date": to_date, "boolean": to_bool}[kind](s)
    unfit = int((out.isna() & ~is_empty(s)).sum())
    if kind == "integer":
        # A fraction in an Integer field doesn't fit: the type was fixed by the first chunk
        out = out.where(out.isna() | (out == out.round()) & (out.abs() < 2 ** 53))
        unfit = int((out.isna() & ~is_empty(s)).sum())
        out = with_default(out.astype("Int64"), None if num_default is None else int(num_default))
    elif kind == "decimal":
        out = with_default(out, num_default)
    elif kind == "date":
        out = with_default(out, dt_default)
    return out, unfit


def keep_type(s: pd.Series) -> pd.Series:
    """A field that already has a type keeps it; the number and date defaults still apply."""
    if pd.api.types.is_bool_dtype(s.dtype):
        return s
    if pd.api.types.is_numeric_dtype(s.dtype):
        return with_default(s, num_default)
    return with_default(s, dt_default if dt_default is None or s.dt.tz is None else dt_default.tz_localize("UTC"))


# The type of each text field is decided from the first chunk of data and then kept, so every chunk is written
# with the same schema (Omniscope's streaming API requires it). Later values that don't fit the type become
# missing, and the block's message counts them.
kinds = None
unfit_counts = {}


def handle_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    global kinds
    groups = {}
    for c in chunk.columns:
        groups.setdefault(norm(c), []).append(c)

    merged = {name: coalesce_cols(chunk, cols) if len(cols) > 1 else chunk[cols[0]] for name, cols in groups.items()}
    chosen = kinds
    if chosen is None:
        chosen = {name: "kept" if not is_text(s) else choose_type(s) for name, s in merged.items()}
        if len(chunk):  # an empty chunk has nothing to judge the types by
            kinds = chosen

    out = pd.DataFrame(index=chunk.index)
    for name, s in merged.items():
        if chosen[name] == "kept":
            out[name] = keep_type(s)
            continue
        out[name], unfit = cast(s, chosen[name])
        if unfit:
            unfit_counts[name] = unfit_counts.get(name, 0) + unfit

    if sort_columns:
        out = out[sorted(out.columns)]
    if unfit_counts:
        api.update_message(unfit_message())
    return out


def unfit_message():
    return ("Values that didn't fit their field's type (now empty): "
            + ", ".join(f"{k} {v}" for k, v in unfit_counts.items()))


api.process_stream(handle_chunk)

# The data stream is over: no more data can be read or written.
api.close(unfit_message() if unfit_counts else "")
