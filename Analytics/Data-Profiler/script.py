"""Data Profiler: one record of statistics per field, and the input records with z-scores and anomaly flags."""
import numpy as np
import pandas as pd
from scipy import stats
from omniscope.api import OmniscopeApi

api = OmniscopeApi()

input_data = api.read_input_records(input_number=0)
if input_data is None:
    api.abort("Connect a data source to the block's input.")

chosen = api.get_option("fields")
threshold = api.get_option("threshold")
if threshold is None or threshold == "":
    threshold = 3.0
try:
    threshold = float(threshold)
except (TypeError, ValueError):
    api.abort("Anomaly threshold must be a number of standard deviations, such as 3.")
if not threshold > 0:
    api.abort("Anomaly threshold must be greater than 0 (3 is usual).")

if chosen:
    missing = [f for f in chosen if f not in input_data.columns]
    if missing:
        api.abort("Fields to profile: not in the input: " + ", ".join(missing))
    fields = [f for f in input_data.columns if f in set(chosen)]
else:
    fields = list(input_data.columns)


def omniscope_type(series):
    """The Omniscope field type a pandas column becomes."""
    dtype = series.dtype
    if pd.api.types.is_bool_dtype(dtype):
        return "Boolean"
    if pd.api.types.is_integer_dtype(dtype):
        return "Integer"
    if pd.api.types.is_float_dtype(dtype):
        return "Decimal"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "Date"
    return "Text"


def as_text(value, kind):
    """A value written as text for the Most common field."""
    if kind == "Integer":
        return str(int(value))
    if kind == "Decimal":
        return f"{float(value):.10g}"
    if kind == "Date":
        ts = pd.Timestamp(value)
        return ts.strftime("%Y-%m-%d") if ts == ts.normalize() else ts.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


STAT_FIELDS = ["Mean", "Std dev", "Min", "Lower quartile", "Median", "Upper quartile", "Max", "Skewness"]

rows = []
records = input_data.copy()
z_cols, flag_cols, p_cols = [], [], []
anomaly_count = pd.Series(0, index=records.index, dtype="int64")

for name in fields:
    col = input_data[name]
    kind = omniscope_type(col)
    present = col.dropna()
    n = len(col)
    row = {
        "Field": str(name),
        "Type": kind,
        "Records": n,
        "Missing": int(n - len(present)),
        "Missing %": round(100.0 * (n - len(present)) / n, 4) if n else np.nan,
        "Distinct": int(present.nunique()),
        "Most common": None,
        "Most common count": pd.NA,
    }
    row.update({k: np.nan for k in STAT_FIELDS})
    row.update({"First date": pd.NaT, "Last date": pd.NaT, "Anomalies": pd.NA})

    if len(present):
        # Most common value, when any value occurs more than once. Ties go to the lowest value (numbers and
        # dates in order, text alphabetically), so the result never depends on the order of the records.
        counts = present.value_counts()
        if counts.max() > 1:
            top = list(counts[counts == counts.max()].index)
            key = (lambda v: as_text(v, kind)) if kind in ("Text", "Boolean") else (lambda v: v)
            row["Most common"] = as_text(sorted(top, key=key)[0], kind)
            row["Most common count"] = int(counts.max())

    if kind in ("Integer", "Decimal"):
        values = present.astype("float64")
        if len(values):
            q = values.quantile([0.25, 0.5, 0.75])
            row.update({
                "Mean": values.mean(),
                "Std dev": values.std(ddof=1) if len(values) > 1 else np.nan,
                "Min": values.min(),
                "Lower quartile": q.loc[0.25],
                "Median": q.loc[0.5],
                "Upper quartile": q.loc[0.75],
                "Max": values.max(),
                "Skewness": values.skew() if len(values) > 2 else np.nan,
            })
        # z-scores against the same mean and standard deviation the statistics output shows
        mean, std = row["Mean"], row["Std dev"]
        full = col.astype("float64")
        if len(values) > 1 and std > 0:
            z = (full - mean) / std
        else:
            z = pd.Series(np.nan, index=col.index)
        flag = pd.Series(pd.array([pd.NA] * n, dtype="Int64"), index=col.index)
        has_z = z.notna()
        flag[has_z] = (z[has_z].abs() >= threshold).astype("int64")
        p = pd.Series(np.nan, index=col.index)
        p[has_z] = 2.0 * stats.norm.sf(z[has_z].abs())
        row["Anomalies"] = int(flag.fillna(0).sum())
        anomaly_count += flag.fillna(0).astype("int64")
        records[f"{name}_z_score"] = z
        records[f"{name}_anomaly"] = flag
        records[f"{name}_p_value"] = p
        z_cols.append(f"{name}_z_score")
        flag_cols.append(f"{name}_anomaly")
        p_cols.append(f"{name}_p_value")
    elif kind == "Date" and len(present):
        row["First date"] = present.min()
        row["Last date"] = present.max()

    rows.append(row)

columns = ["Field", "Type", "Records", "Missing", "Missing %", "Distinct", "Most common", "Most common count"] \
    + STAT_FIELDS + ["First date", "Last date", "Anomalies"]
profile = pd.DataFrame(rows, columns=columns)
for c in ("Records", "Missing", "Distinct", "Most common count", "Anomalies"):
    profile[c] = pd.array(profile[c].tolist(), dtype="Int64")
for c in ["Missing %"] + STAT_FIELDS:
    profile[c] = profile[c].astype("float64")
profile["Most common"] = profile["Most common"].astype(object)
profile["Field"] = profile["Field"].astype(object)
profile["Type"] = profile["Type"].astype(object)
# Date columns: keep the input's time zone (Omniscope dates arrive in UTC)
date_tz = next((input_data[f].dt.tz for f in fields if omniscope_type(input_data[f]) == "Date"), None)
for c in ("First date", "Last date"):
    d = pd.to_datetime(profile[c].tolist(), utc=True) if len(profile) else pd.DatetimeIndex([], tz="UTC")
    profile[c] = d if date_tz is not None else d.tz_localize(None)

original = [c for c in records.columns if c not in set(z_cols + flag_cols + p_cols + ["Anomaly count"])]
records["Anomaly count"] = anomaly_count
records = records[original + z_cols + flag_cols + p_cols + ["Anomaly count"]]

api.write_output(profile, "Output Data")
api.write_output(records, "Output Data 2")
flagged = int((anomaly_count > 0).sum())
api.commit(f"Profiled {len(fields)} fields; {flagged} of {len(records)} records have a value "
           f"{threshold:g} or more standard deviations from its field's mean.")
