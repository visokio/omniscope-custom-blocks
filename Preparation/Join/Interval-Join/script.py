import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

left = omniscope_api.read_input_records(input_number=0)
right = omniscope_api.read_input_records(input_number=1)

value_field = omniscope_api.get_option("value")
start_field = omniscope_api.get_option("start")
start_comparator = omniscope_api.get_option("start_comparator") or ">="
end_field = omniscope_api.get_option("end")
end_comparator = omniscope_api.get_option("end_comparator") or "<"
join_type = omniscope_api.get_option("join_type") or "INNER"
left_eq_field = omniscope_api.get_option("left")
right_eq_field = omniscope_api.get_option("right")

if left is None:
    omniscope_api.abort("Connect the records with the values to the first input.")
if right is None:
    omniscope_api.abort("Connect the intervals to the second input.")

for name, field, data, which in [("Value in interval", value_field, left, "first"),
                                 ("Interval start", start_field, right, "second"),
                                 ("Interval end", end_field, right, "second")]:
    if not field:
        omniscope_api.abort(f"Choose the \"{name}\" field.")
    if field not in data.columns:
        omniscope_api.abort(f"The {which} input has no field called \"{field}\" (\"{name}\").")

if bool(left_eq_field) != bool(right_eq_field):
    omniscope_api.abort("To match on a field as well, choose it for both inputs; or clear both.")
for field, data, which in [(left_eq_field, left, "first"), (right_eq_field, right, "second")]:
    if field and field not in data.columns:
        omniscope_api.abort(f"The {which} input has no field called \"{field}\".")


def kind(series):
    dtype = series.dtype
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "date"
    if pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_bool_dtype(dtype):
        return "number"
    if series.isna().all():
        return "empty"  # a field with no values at all: fits either kind
    return "other"


kinds = {f: kind(d[f]) for f, d in [(value_field, left), (start_field, right), (end_field, right)]}
bad = [f for f, k in kinds.items() if k == "other"]
if bad:
    omniscope_api.abort("The value, start and end fields must be numbers or dates; "
                        + ", ".join(f"\"{f}\"" for f in bad) + " is not.")
used = {k for k in kinds.values() if k != "empty"}
if len(used) > 1:
    omniscope_api.abort("The value, start and end fields must be all numbers or all dates.")
is_date = used == {"date"}


def as_array(series, missing):
    """Comparable numpy values: nanoseconds for dates (UTC), floats for numbers; missing -> `missing`."""
    if is_date:
        s = pd.to_datetime(series, utc=True)
        out = s.dt.tz_localize(None).astype("datetime64[ns]").to_numpy().astype("int64")
        out[s.isna().to_numpy()] = missing
        return out
    s = pd.to_numeric(series, errors="coerce").astype("float64").to_numpy()
    return np.where(np.isnan(s), missing, s)


if is_date:
    low, high = np.iinfo("int64").min + 1, np.iinfo("int64").max
else:
    low, high = -np.inf, np.inf

values = as_array(left[value_field], 0)
value_missing = left[value_field].isna().to_numpy()
starts = as_array(right[start_field], low)  # an empty start has no lower limit
ends = as_array(right[end_field], high)  # an empty end has no upper limit
usable = starts <= ends  # an interval that ends before it starts never matches
skipped_intervals = int((~usable).sum())

start_ok = np.greater_equal if start_comparator == ">=" else np.greater
end_ok = np.less_equal if end_comparator == "<=" else np.less


def groups(data, field, rows):
    """Row positions (among `rows`) per value of the equality field; one group of all rows when there is none."""
    if not field:
        return {None: rows}
    keys = data[field].to_numpy()[rows]
    present = ~pd.isna(keys)
    frame = pd.DataFrame({"k": keys[present], "pos": rows[present]})
    return {k: g["pos"].to_numpy() for k, g in frame.groupby("k", sort=False)}


left_groups = groups(left, left_eq_field, np.nonzero(~value_missing)[0])
right_groups = groups(right, right_eq_field, np.nonzero(usable)[0])

CHUNK = 2048
pairs_left, pairs_right = [], []
for key, lpos in left_groups.items():
    rpos = right_groups.get(key)
    if rpos is None or len(lpos) == 0:
        continue
    order = np.argsort(starts[rpos], kind="stable")
    rpos = rpos[order]
    s, e = starts[rpos], ends[rpos]
    lpos = lpos[np.argsort(values[lpos], kind="stable")]
    v_all = values[lpos]
    for c in range(0, len(lpos), CHUNK):
        v = v_all[c:c + CHUNK]
        # candidates: intervals starting at or before the chunk's largest value and ending at or after its smallest
        k = np.searchsorted(s, v[-1], side="right")
        cand = np.nonzero(e[:k] >= v[0])[0]
        if len(cand) == 0:
            continue
        hit = start_ok(v[:, None], s[cand][None, :]) & end_ok(v[:, None], e[cand][None, :])
        li, ri = np.nonzero(hit)
        pairs_left.append(lpos[c:c + CHUNK][li])
        pairs_right.append(rpos[cand][ri])

pl = np.concatenate(pairs_left) if pairs_left else np.array([], dtype=int)
pr = np.concatenate(pairs_right) if pairs_right else np.array([], dtype=int)

if join_type == "LEFT":
    unmatched = np.setdiff1d(np.arange(len(left)), pl)
    pl = np.concatenate([pl, unmatched])
    pr = np.concatenate([pr, np.full(len(unmatched), -1)])

# first input's order, then the second input's
order = np.lexsort((pr, pl))
pl, pr = pl[order], pr[order]

left_part = left.reset_index(drop=True).iloc[pl].reset_index(drop=True)
right_part = right.reset_index(drop=True).reindex(pr).reset_index(drop=True)  # -1: no interval, empty fields


def dedup_names(names):
    names = list(names)
    counts = {}
    for i, col in enumerate(names):
        cur_count = counts.get(col, 0)
        if cur_count > 0:
            names[i] = "%s.%d" % (col, cur_count)
        counts[col] = cur_count + 1
    return names


output_data = pd.concat([left_part, right_part], axis=1)
while output_data.columns.duplicated().any():  # a field in both inputs: the second one gets ".1"
    output_data.columns = dedup_names(output_data.columns)

matched = len(np.unique(pl[pr >= 0]))
message = f"{matched} of {len(left)} records in an interval; {len(output_data)} records out"
if skipped_intervals:
    message += f"; {skipped_intervals} intervals end before they start and were ignored"

omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close(message)
