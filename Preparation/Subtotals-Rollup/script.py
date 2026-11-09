"""Subtotals and Rollup: aggregate by a hierarchy of fields (for example
Division > Region > Store) and add a subtotal row for every level and a grand
total, in report order, the classic finance and management table.

Each row carries its level, a row type (Detail, Subtotal, Grand total), an
indented label for display, the aggregated values, and for the first value
field the share of its parent and of the grand total. Children can be sorted
by value (largest first) or by name within each parent.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


levels = list(opt("group_fields", []) or [])
values = list(opt("value_fields", []) or [])
agg = opt("aggregation", "SUM")
order = opt("sort", "VALUE")
total_label = opt("total_label", "Total")
grand = bool(opt("grand_total", True))
subtotals_at = opt("subtotal_position", "BEFORE")

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
if not levels:
    omniscope_api.abort("Choose the group fields, outermost first (for example Division, Region, Store).")
miss = [f for f in levels + values if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")
if not values and agg != "COUNT":
    omniscope_api.abort("Choose at least one value field, or count rows.")
w = df[levels].astype(object).where(df[levels].notna(), "(blank)").astype(str)
for v in values:
    w[v] = pd.to_numeric(df[v], errors="coerce").astype("float64")
    if df[v].notna().any() and w[v].isna().all():
        omniscope_api.abort(f"Value field '{v}' must be numeric.")
w["__n"] = 1
FN = {"SUM": "sum", "MEAN": "mean", "MIN": "min", "MAX": "max", "COUNT": "sum", "MEDIAN": "median"}[agg]


def aggregate(keys):
    spec = {"Rows": ("__n", "sum")}
    for v in values:
        spec[v] = (v, FN) if agg != "COUNT" else (v, "count")
    g = w.groupby(keys, sort=False).agg(**spec).reset_index() if keys else pd.DataFrame([{**{"Rows": len(w)}, **{v: (getattr(w[v], FN)() if agg != "COUNT" else w[v].count()) for v in values}}])
    return g


tables = {k: aggregate(levels[:k]) for k in range(0, len(levels) + 1)}
main = values[0] if values else "Rows"
INDENT = "\u00b7 "  # a visible mark: Omniscope trims leading spaces (even non-breaking ones) from text a block writes
out = []


def emit(prefix, depth, parent_val, grand_val):
    t = tables[depth + 1]
    sub = t
    for i, val in enumerate(prefix):
        sub = sub[sub[levels[i]] == val]
    sub = sub.sort_values(main, ascending=False, kind="mergesort") if order == "VALUE" else sub.sort_values(levels[depth], kind="mergesort")
    for _, r in sub.iterrows():
        key = prefix + [r[levels[depth]]]
        is_leaf = depth + 1 == len(levels)
        row = {**{levels[i]: key[i] if i < len(key) else None for i in range(len(levels))},
               "Level": depth + 1, "Row Type": "Detail" if is_leaf else "Subtotal",
               "Label": INDENT * depth + str(key[-1]), "Rows": int(r["Rows"]), **{v: r[v] for v in values},
               "Share Of Parent": r[main] / parent_val if parent_val else np.nan, "Share Of Total": r[main] / grand_val if grand_val else np.nan}
        if not is_leaf:
            if subtotals_at == "BEFORE":
                out.append(row)
            emit(key, depth + 1, r[main], grand_val)
            if subtotals_at == "AFTER":
                row["Label"] = INDENT * depth + f"{key[-1]} {total_label}"
                out.append(row)
        else:
            out.append(row)


g0 = tables[0].iloc[0]
grand_val = g0[main] if main in g0 else g0["Rows"]
grow = {**{lv: total_label for lv in levels}, "Level": 0, "Row Type": "Grand total", "Label": total_label, "Rows": int(g0["Rows"]),
        **{v: g0[v] for v in values}, "Share Of Parent": np.nan, "Share Of Total": 1.0}
if len(w):
    if grand and subtotals_at == "BEFORE":
        out.append(grow)
    emit([], 0, grand_val, grand_val)
    if grand and subtotals_at == "AFTER":
        out.append(grow)
cols = levels + ["Level", "Row Type", "Label", "Rows"] + values + ["Share Of Parent", "Share Of Total"]
res = pd.DataFrame(out, columns=cols)
for lv in levels:
    res[lv] = res[lv].astype(object).where(res[lv].notna(), None)
res.insert(0, "Order", np.arange(1, len(res) + 1))
for c in ("Order", "Level", "Rows"):
    res[c] = res[c].astype("int64")
for c in values + ["Share Of Parent", "Share Of Total"]:
    res[c] = res[c].astype("float64")
omniscope_api.write_output(res, "rollup")
omniscope_api.close(f"{len(res):,} rows: {int((res['Row Type'] == 'Detail').sum()):,} detail, {int((res['Row Type'] == 'Subtotal').sum()):,} subtotals"
                    + (", 1 grand total" if grand and len(res) else "") + f" ({agg.lower()} of {', '.join(values) or 'rows'}).")
