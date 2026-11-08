from omniscope.api import OmniscopeApi
import pandas as pd

omni = OmniscopeApi()

# --- Get options ---
date_fields = omni.get_option("dateFields")
timezone_handling = omni.get_option("timezoneHandling") or "PRESERVE_LOCAL"

if not date_fields:
    omni.abort("Choose at least one date field to expand.")
    raise SystemExit

# In case Omniscope returns a single string instead of a list
if isinstance(date_fields, str):
    date_fields = [date_fields]

# --- Read input data ---
df = omni.read_input_records(0)

if df is None:
    omni.abort("Connect a data source to the block's input.")
    raise SystemExit

# Check all selected fields exist
missing = [f for f in date_fields if f not in df.columns]
if missing:
    omni.abort("Selected fields not found in input: " + ", ".join(missing))
    raise SystemExit

# A number would otherwise be read as nanoseconds since 1970
not_dates = [f for f in date_fields
             if not (pd.api.types.is_datetime64_any_dtype(df[f].dtype)
                     or pd.api.types.is_string_dtype(df[f].dtype)
                     or pd.api.types.is_object_dtype(df[f].dtype))]
if not_dates:
    omni.abort("These fields are not Date fields: " + ", ".join(not_dates)
               + ". Convert them to dates first (for example with Field Organiser).")
    raise SystemExit

# Deterministic English names, independent of machine locale
MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

DAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def parse_one_date(value):
    """Parse one value independently so mixed offsets do not break the Series."""
    if value is None or pd.isna(value):
        return pd.NaT

    try:
        return pd.Timestamp(value)
    except (ValueError, TypeError, OverflowError):
        return pd.NaT


def remove_timezone_without_conversion(value):
    """Remove timezone information while preserving local clock/calendar values."""
    if pd.isna(value):
        return pd.NaT

    if value.tzinfo is not None:
        return value.tz_localize(None)

    return value


def timezone_signature(value):
    """Return a comparable signature for timezone consistency checks."""
    if pd.isna(value):
        return None

    if value.tzinfo is None:
        return ("naive",)

    tz = value.tzinfo
    name = getattr(tz, "key", None) or getattr(tz, "zone", None)

    if name:
        return ("aware", name)

    # ISO timestamps often only carry a fixed UTC offset.
    return ("aware", str(value.utcoffset()))


def prepare_dates(series, handling):
    """Normalise a date Series according to the selected timezone behaviour."""
    if handling == "CONVERT_TO_UTC":
        # Explicitly supports mixed UTC offsets (e.g. DST changes).
        dates = pd.to_datetime(series, errors="coerce", utc=True)
        # This block only needs calendar/date parts, so return timezone-naive UTC.
        return dates.dt.tz_localize(None)

    if handling not in ("PRESERVE_LOCAL", "REJECT_MIXED"):
        raise ValueError(
            "Unknown timezone handling mode: " + str(handling)
        )

    # Parse values independently. This avoids pandas trying to create a single
    # DatetimeIndex from values with different UTC offsets.
    parsed = series.map(parse_one_date)

    if handling == "REJECT_MIXED":
        signatures = {
            timezone_signature(value)
            for value in parsed
            if not pd.isna(value)
        }
        signatures.discard(None)

        if len(signatures) > 1:
            raise ValueError(
                "Mixed timezone offsets, or a mixture of timezone-aware and "
                "timezone-naive values, were detected."
            )

    # preserveLocal and rejectMixed both remove timezone metadata without
    # shifting the displayed date/time.
    stripped = parsed.map(remove_timezone_without_conversion)
    return pd.to_datetime(stripped, errors="coerce")


def flag(values, dates):
    """True/False for a date, empty for a missing date."""
    return values.astype("boolean").mask(dates.isna())


empty_fields = []

# --- Expand each date field ---
# Every chosen field always gets the same set of new fields, so the output's fields never depend on the data.
for field in date_fields:
    try:
        dates = prepare_dates(df[field], timezone_handling)
    except ValueError as exc:
        omni.abort(
            f"Unable to process date field '{field}': {exc} "
            "Change the 'Time zones' option or normalise the field upstream."
        )
        raise SystemExit

    if len(dates) and dates.isna().all():
        empty_fields.append(field)

    prefix = field
    iso = dates.dt.isocalendar()

    df[f"{prefix}_year"] = dates.dt.year.astype("Int64")
    df[f"{prefix}_month"] = dates.dt.month.astype("Int64")
    df[f"{prefix}_month_name"] = dates.dt.month.map(MONTH_NAMES)
    df[f"{prefix}_day"] = dates.dt.day.astype("Int64")
    df[f"{prefix}_day_name"] = dates.dt.dayofweek.map(DAY_NAMES)
    df[f"{prefix}_dayofyear"] = dates.dt.dayofyear.astype("Int64")
    df[f"{prefix}_quarter"] = dates.dt.quarter.astype("Int64")
    df[f"{prefix}_is_month_start"] = flag(dates.dt.is_month_start, dates)
    df[f"{prefix}_is_month_end"] = flag(dates.dt.is_month_end, dates)

    # ISO week of year, and the ISO year it belongs to (29 December 2025 is in week 1 of 2026)
    df[f"{prefix}_weekofyear"] = iso.week.astype("Int64")
    df[f"{prefix}_week_year"] = iso.year.astype("Int64")

# --- Output ---
omni.write_output_records(df, 0)

message = "Expanded " + ", ".join(date_fields) + "."
if empty_fields:
    message += " No dates in " + ", ".join(empty_fields) + ": its date parts are empty."
omni.commit(message)
