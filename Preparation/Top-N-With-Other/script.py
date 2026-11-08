"""Top N With Other: keep the N largest items per group (by a value) and roll
everything else into one "Other" row, so pie charts, bar charts and tables stay
readable: top 10 products per region, top 5 suppliers per category plus Other.

A minimum share of the group can be required as well (or instead, with N = 0). Values are summed per group and item first. Each output row carries its
rank, share of group, cumulative share and how many items "Other" holds.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


item_f, val_f = opt("item_field"), opt("value_field")
group_fields = list(opt("group_fields", []) or [])
extra = [f for f in (opt("extra_value_fields", []) or []) if f != val_f]
n_keep = int(opt("top_n", 10))
min_share = float(opt("min_share", 0) or 0)
other_label = opt("other_label", "Other")
include_other = bool(opt("include_other", True))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
for f, lab in ((item_f, "item"), (val_f, "value")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
miss = [f for f in group_fields + extra if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")
if n_keep < 1 and min_share <= 0:
    omniscope_api.abort("Keep at least 1 item, or set a minimum share.")
w = df[group_fields].astype(object).where(df[group_fields].notna(), "(blank)").astype(str) if group_fields else pd.DataFrame(index=df.index)
w["__i"] = df[item_f].astype(object).where(df[item_f].notna(), "(blank)").map(str)
for f in [val_f] + extra:
    w[f] = pd.to_numeric(df[f], errors="coerce").astype("float64")
if df[val_f].notna().any() and w[val_f].isna().all():
    omniscope_api.abort(f"The value field '{val_f}' must be numeric.")
agg = w.groupby(group_fields + ["__i"], sort=False)[[val_f] + extra].sum().reset_index()
rows = []
for key, g in (agg.groupby(group_fields, sort=True) if group_fields else [((), agg)]):
    key = key if isinstance(key, tuple) else (key,)
    gd = dict(zip(group_fields, key))
    g = g.sort_values([val_f, "__i"], ascending=[False, True], kind="mergesort").reset_index(drop=True)
    tot = g[val_f].sum()
    share = g[val_f] / tot if tot else pd.Series(np.nan, index=g.index)
    # top N (0 = no limit), and with a minimum share also drop items below it
    keep = np.ones(len(g), dtype=bool) if n_keep < 1 else (np.arange(len(g)) < n_keep)
    if min_share > 0:
        keep &= share.to_numpy() >= min_share
    cum = 0.0
    for r, (_, x) in enumerate(g[keep].iterrows(), start=1):
        cum += x[val_f] / tot if tot else np.nan
        rows.append({**gd, str(item_f): x["__i"], "Rank": r, val_f: x[val_f], **{e: x[e] for e in extra},
                     "Share Of Group": x[val_f] / tot if tot else np.nan, "Cumulative Share": cum, "Items Included": 1, "Is Other": "No"})
    rest = g[~keep]
    if include_other and len(rest):
        rows.append({**gd, str(item_f): other_label, "Rank": int(keep.sum()) + 1, val_f: rest[val_f].sum(), **{e: rest[e].sum() for e in extra},
                     "Share Of Group": rest[val_f].sum() / tot if tot else np.nan, "Cumulative Share": 1.0 if tot else np.nan,
                     "Items Included": int(len(rest)), "Is Other": "Yes"})
cols = group_fields + [str(item_f), "Rank", val_f] + extra + ["Share Of Group", "Cumulative Share", "Items Included", "Is Other"]
out = pd.DataFrame(rows, columns=cols)
for c in ("Rank", "Items Included"):
    out[c] = out[c].astype("int64")
for c in [val_f] + extra + ["Share Of Group", "Cumulative Share"]:
    out[c] = out[c].astype("float64")
omniscope_api.write_output(out, "top")
n_other = int((out["Is Other"] == "Yes").sum())
omniscope_api.close(f"{int((out['Is Other'] == 'No').sum()):,} items kept across {max(1, out[group_fields].drop_duplicates().shape[0]) if group_fields else 1:,} group(s)"
                    + (f"; {int(out.loc[out['Is Other'] == 'Yes', 'Items Included'].sum()):,} items rolled into {n_other} '{other_label}' row(s)" if n_other else "") + ".")
