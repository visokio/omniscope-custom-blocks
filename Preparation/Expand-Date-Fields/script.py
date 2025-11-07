from omniscope.api import OmniscopeApi
import pandas as pd
import locale

# Try to force English day/month names
try:
    locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
except locale.Error:
    # If locale isn't available, pandas defaults are usually English anyway
    pass

omni = OmniscopeApi()

# --- Get the selected date fields (array) ---
date_fields = omni.get_option("dateFields")

if not date_fields:
    omni.abort("The 'Date fields' option must contain at least one field.")
    raise SystemExit

# In case Omniscope returns a single string instead of a list
if isinstance(date_fields, str):
    date_fields = [date_fields]

# --- Read input data ---
df = omni.read_input_records(0)

if df is None or df.empty:
    omni.write_output_records(pd.DataFrame(), 0)
    omni.commit("No input data.")
    raise SystemExit

# Check all selected fields exist
missing = [f for f in date_fields if f not in df.columns]
if missing:
    omni.abort("Selected fields not found in input: " + ", ".join(missing))
    raise SystemExit

processed = []

# --- Expand each date field ---
for field in date_fields:
    dates = pd.to_datetime(df[field], errors="coerce")

    if dates.isna().all():
        # Skip completely invalid fields (shouldn't really happen if Omniscope enforces type)
        continue

    prefix = field  # use field name as prefix

    df[f"{prefix}_year"]         = dates.dt.year
    df[f"{prefix}_month"]        = dates.dt.month
    df[f"{prefix}_month_name"]   = dates.dt.month_name()   # English month name
    df[f"{prefix}_day"]          = dates.dt.day
    df[f"{prefix}_day_name"]     = dates.dt.day_name()     # English day name
    df[f"{prefix}_dayofyear"]    = dates.dt.dayofyear
    df[f"{prefix}_quarter"]      = dates.dt.quarter
    df[f"{prefix}_is_month_start"] = dates.dt.is_month_start
    df[f"{prefix}_is_month_end"]   = dates.dt.is_month_end

    # ISO week of year
    try:
        df[f"{prefix}_weekofyear"] = dates.dt.isocalendar().week.astype("Int64")
    except AttributeError:
        # Older pandas
        df[f"{prefix}_weekofyear"] = dates.dt.week

    processed.append(field)

# --- Output ---
omni.write_output_records(df, 0)

if processed:
    omni.commit(
        "Expanded date parts for fields: " + ", ".join(processed)
    )
else:
    omni.abort("None of the selected fields contained valid dates.")
    raise SystemExit