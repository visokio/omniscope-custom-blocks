import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

fixed_fields = omniscope_api.get_option("fixed_fields") or []
var_name = (omniscope_api.get_option("var_name") or "").strip()
value_name = (omniscope_api.get_option("value_name") or "").strip()
drop_empty = bool(omniscope_api.get_option("drop_empty"))

input_data = omniscope_api.read_input_records(input_number=0)
if input_data is None:
    omniscope_api.abort("Connect the records to de-pivot to the block's input.")

if isinstance(fixed_fields, str):
    fixed_fields = [fixed_fields]
fixed_fields = [f for f in fixed_fields if f]
unknown = [f for f in fixed_fields if f not in input_data.columns]
if unknown:
    omniscope_api.abort("The input has no field called " + ", ".join(f"\"{f}\"" for f in unknown) + ".")
if not var_name or not value_name:
    omniscope_api.abort("Give names for the two new fields (field names and values).")
if var_name == value_name:
    omniscope_api.abort("The two new fields need different names.")
for name in (var_name, value_name):
    if name in fixed_fields:
        omniscope_api.abort(f"\"{name}\" is already a fixed field: choose another name for the new field.")

variable_fields = [c for c in input_data.columns if c not in fixed_fields]


def kind(dtype):
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "date"
    if pd.api.types.is_numeric_dtype(dtype):
        return "number"
    return "text"


def as_text(series):
    """Values of one field as text, the way they read: whole numbers without ".0", dates without a midnight time."""
    k = kind(series.dtype)
    if k == "number":
        def fmt(v):
            v = float(v)
            return str(int(v)) if v.is_integer() and abs(v) < 2**53 else repr(v)
        return series.map(lambda v: None if pd.isna(v) else fmt(v)).astype(object)
    if k == "date":
        s = series.dt.tz_localize(None) if series.dt.tz is not None else series
        has_time = (s.dropna() != s.dropna().dt.normalize()).any()
        text = s.dt.strftime("%Y-%m-%d %H:%M:%S" if has_time else "%Y-%m-%d")
        return text.where(s.notna(), None).astype(object)
    if k == "boolean":
        return series.map(lambda v: None if pd.isna(v) else ("true" if v else "false")).astype(object)
    return series.astype(object).where(series.notna(), None)


kinds = {kind(input_data[c].dtype) for c in variable_fields}
data = input_data
if len(kinds) > 1:
    # Fields of different types share one value field: make them all text, so no value changes type silently
    data = input_data.copy()
    for c in variable_fields:
        data[c] = as_text(data[c])

result = data.melt(id_vars=fixed_fields, value_vars=variable_fields, var_name=var_name, value_name=value_name)

# Each input record's values together, in field order (melt gives all records for the first field, then the next)
n = len(data)
order = np.arange(len(result)).reshape(len(variable_fields), n).T.ravel() if n and variable_fields else []
result = result.iloc[order].reset_index(drop=True)

dropped = 0
if drop_empty:
    keep = result[value_name].notna()
    if result[value_name].dtype == object or pd.api.types.is_string_dtype(result[value_name].dtype):
        keep &= result[value_name].astype(str).str.strip() != ""
    dropped = int((~keep).sum())
    result = result[keep].reset_index(drop=True)

message = f"{n} records x {len(variable_fields)} fields de-pivoted: {len(result)} records"
if dropped:
    message += f" ({dropped} empty values left out)"
if len(kinds) > 1:
    message += "; values of different types were turned into text"

omniscope_api.write_output_records(result, output_number=0)
omniscope_api.close(message)
