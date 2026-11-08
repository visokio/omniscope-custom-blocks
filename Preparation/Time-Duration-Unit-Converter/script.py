"""Time Duration Unit Converter: turns times of day and durations into a number of milliseconds, seconds, minutes
or hours, in a new field per chosen field.

- Date fields: the time since midnight (the date part is ignored).
- Text fields: a duration or time such as "08:30", "1:45:20", "1 day 02:00:00", "90 min", "1h 30m" or "PT1H30M".
"""
import re

import pandas as pd
from omniscope.api import OmniscopeApi

UNITS = {"ms": pd.Timedelta(milliseconds=1), "s": pd.Timedelta(seconds=1),
         "m": pd.Timedelta(minutes=1), "h": pd.Timedelta(hours=1)}
HOURS_MINUTES = re.compile(r"^-?\d+:\d{1,2}$")  # "8:30": hours and minutes, which pandas does not read alone
BARE_NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)$")  # pandas would read "3" as 3 nanoseconds

omni = OmniscopeApi()

fields = omni.get_option("date_fields") or []
if isinstance(fields, str):
    fields = [fields]
unit = omni.get_option("unit") or "s"

if not fields:
    omni.abort("Choose at least one field to convert.")
if unit not in UNITS:
    omni.abort(f"Unknown unit '{unit}'.")

df = omni.read_input_records(input_number=0)
if df is None:
    omni.abort("Connect the records to convert to the block's input.")


def text_to_timedelta(values: pd.Series) -> pd.Series:
    def clean(v):
        if pd.isna(v):
            return None
        v = str(v).strip()
        if BARE_NUMBER.match(v):
            return "not a duration"  # no unit: left empty and counted
        return v + ":00" if HOURS_MINUTES.match(v) else v

    text = pd.Series([clean(v) for v in values], index=values.index, dtype=object)
    # each distinct text is read once; anything pandas can't read as a duration is left empty
    distinct = pd.Series(pd.unique(text.dropna()), dtype=object)
    read = pd.to_timedelta(distinct, errors="coerce")
    return pd.to_timedelta(text.map(dict(zip(distinct, read))))


unreadable = {}
for field in fields:
    if field not in df.columns:
        omni.abort(f"The field '{field}' is not in the input.")
    values = df[field]
    if pd.api.types.is_datetime64_any_dtype(values):
        durations = values - values.dt.normalize()  # time since midnight; missing dates stay missing
    elif pd.api.types.is_timedelta64_dtype(values):
        durations = values
    elif pd.api.types.is_string_dtype(values.dtype) or pd.api.types.is_object_dtype(values.dtype):
        durations = text_to_timedelta(values)
        failed = int((durations.isna() & values.notna()).sum())
        if failed:
            unreadable[field] = failed
    else:
        omni.abort(f"'{field}' is a number field; choose Date or Text fields. "
                   "To convert a number between units, use a formula.")
    df[f"{field}_{unit}"] = (durations / UNITS[unit]).astype("float64")

if unreadable:
    omni.update_message("Not read as a time or duration (left empty): "
                        + ", ".join(f"{n} in {f}" for f, n in unreadable.items()))

omni.write_output_records(df, output_number=0)
omni.commit()
