from omniscope.api import OmniscopeApi
import pandas as pd
import datetime

# ─── Utility: any datetime/timedelta/text → time in given unit ────────────────
def value_to_duration(val, unit: str = "ms") -> float:
    if val is None or (isinstance(val, pd.Timestamp) and pd.isna(val)):
        return None
    if isinstance(val, pd.Timestamp):
        dt = val.to_pydatetime()
        td = datetime.timedelta(
            hours=dt.hour, minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond
        )
    elif isinstance(val, datetime.datetime):
        td = datetime.timedelta(
            hours=val.hour, minutes=val.minute, seconds=val.second, microseconds=val.microsecond
        )
    elif isinstance(val, pd.Timedelta):
        td = val
    elif isinstance(val, str):
        try:
            td = pd.to_timedelta(val)
        except:
            return None
    else:
        return None

    # Convert to desired unit
    if unit == "ms":
        return td / pd.Timedelta(1, "ms")
    elif unit == "s":
        return td / pd.Timedelta(1, "s")
    elif unit == "m":
        return td / pd.Timedelta(1, "m")
    elif unit == "h":
        return td / pd.Timedelta(1, "h")
    else:
        return None  # Unsupported unit

# ─── Main Omniscope block ─────────────────────────────────────────────────────
omni = OmniscopeApi()

date_fields = omni.get_option("date_fields")
unit = omni.get_option("unit")  # e.g., "ms", "s", "m", "h"

df = omni.read_input_records(input_number=0)

for col in date_fields:
    if col in df.columns:
        new_col = f"{col}_{unit}"
        df[new_col] = df[col].apply(lambda val: value_to_duration(val, unit))
    # else: silently skip missing fields

omni.write_output_records(df, output_number=0)
omni.commit()