"""Correlation Matrix: Pearson and Spearman correlations with p-values for
every pair of numeric fields (or each field against one target), overall or
per group, using all rows where both fields have values.

Outputs: one row per pair (ranked by strength), the matrix in long form for a
heat map (field x field), and a wide matrix (one row per field).
Strength labels follow a common convention: |r| < 0.1 negligible, < 0.3 weak,
< 0.5 moderate, < 0.7 strong, otherwise very strong.
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


fields = list(opt("fields", []) or [])
target = opt("target_field")
group_f = opt("group_field")
method = opt("method", "PEARSON")
alpha = float(opt("significance", 0.05))
min_n = int(opt("min_pairs", 10))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
for f in ([target] if target else []) + ([group_f] if group_f else []) + fields:
    if f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")
if not fields:
    fields = [c for c in df.columns if c != group_f and pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]
if target and target not in fields:
    fields = [target] + fields
num = {}
for f in fields:
    v = pd.to_numeric(df[f], errors="coerce").astype("float64")
    if df[f].notna().any() and v.notna().sum() == 0:
        omniscope_api.abort(f"Field '{f}' has no numbers; choose numeric fields.")
    num[f] = v
if len(fields) < 2:
    omniscope_api.abort("Choose at least two numeric fields (or one target and one other).")


def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        de = d * c
        h *= de
        if abs(de - 1) < 3e-14:
            break
    return h


def betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def t_sf2(t, dfree):
    """Two-sided p-value of Student's t."""
    if dfree <= 0 or t != t:
        return float("nan")
    x = dfree / (dfree + t * t)
    return betainc(dfree / 2.0, 0.5, x)


def corr_p(r, n):
    if n < 3 or r != r:
        return float("nan")
    if abs(r) >= 1:
        return 0.0
    t = r * math.sqrt((n - 2) / (1 - r * r))
    return t_sf2(abs(t), n - 2)


def strength(r):
    a = abs(r)
    if a != a:
        return None
    return "Negligible" if a < 0.1 else "Weak" if a < 0.3 else "Moderate" if a < 0.5 else "Strong" if a < 0.7 else "Very strong"


def pair_stats(x, y):
    m = ~(np.isnan(x) | np.isnan(y))
    n = int(m.sum())
    if n < max(3, min_n):
        return n, np.nan, np.nan, np.nan, np.nan
    xx, yy = x[m], y[m]
    pr = float(np.corrcoef(xx, yy)[0, 1]) if xx.std() > 0 and yy.std() > 0 else np.nan
    rx, ry = pd.Series(xx).rank().to_numpy(), pd.Series(yy).rank().to_numpy()
    sr = float(np.corrcoef(rx, ry)[0, 1]) if rx.std() > 0 and ry.std() > 0 else np.nan
    return n, pr, corr_p(pr, n), sr, corr_p(sr, n)


groups = [("All", df.index)] + ([(str(k), g.index) for k, g in df.groupby(df[group_f].astype(object).where(df[group_f].notna(), "(blank)").map(str), sort=True)]
                                if group_f else [])
pairs = [(target, f) for f in fields if f != target] if target else [(fields[i], fields[j]) for i in range(len(fields)) for j in range(i + 1, len(fields))]
rows, cells = [], []
key = "Pearson" if method == "PEARSON" else "Spearman"
for gname, idx in groups:
    cache = {f: num[f].loc[idx].to_numpy() for f in fields}
    for a, b in pairs:
        n, pr, pp, sr, sp = pair_stats(cache[a], cache[b])
        main = pr if method == "PEARSON" else sr
        mp = pp if method == "PEARSON" else sp
        rec = {"Group": gname, "Field A": a, "Field B": b, "Rows": n, "Pearson": pr, "Pearson P Value": pp, "Spearman": sr, "Spearman P Value": sp,
               "Strength": strength(main), "Direction": None if main != main else ("Positive" if main > 0 else "Negative" if main < 0 else "None"),
               "Significant": None if mp != mp else ("Yes" if mp < alpha else "No")}
        rows.append(rec)
        for x_, y_ in ((a, b), (b, a)):
            cells.append({"Group": gname, "Row Field": x_, "Column Field": y_, "Correlation": main, "P Value": mp, "Rows": n})
    if not target:
        for f in fields:
            cells.append({"Group": gname, "Row Field": f, "Column Field": f, "Correlation": 1.0, "P Value": 0.0, "Rows": int((~np.isnan(cache[f])).sum())})
pr_df = pd.DataFrame(rows, columns=["Group", "Field A", "Field B", "Rows", "Pearson", "Pearson P Value", "Spearman", "Spearman P Value", "Strength", "Direction", "Significant"])
pr_df["Abs"] = pr_df[key].abs()
pr_df = pr_df.sort_values(["Group", "Abs"], ascending=[True, False], key=lambda c: c.map(lambda v: (v != "All", v)) if c.name == "Group" else c,
                          kind="mergesort", na_position="last").drop(columns=["Abs"]).reset_index(drop=True)
pr_df["Rank"] = pr_df.groupby("Group").cumcount().astype("int64") + 1
pr_df["Rows"] = pr_df["Rows"].astype("int64")
for c in ("Pearson", "Pearson P Value", "Spearman", "Spearman P Value"):
    pr_df[c] = pr_df[c].astype("float64")
cl = pd.DataFrame(cells, columns=["Group", "Row Field", "Column Field", "Correlation", "P Value", "Rows"])
order = {f: i for i, f in enumerate(fields)}
cl["Row Order"] = cl["Row Field"].map(order).astype("int64")
cl["Column Order"] = cl["Column Field"].map(order).astype("int64")
cl = cl.sort_values(["Group", "Row Order", "Column Order"], key=lambda c: c.map(lambda v: (v != "All", v)) if c.name == "Group" else c, kind="mergesort").reset_index(drop=True)
cl["Rows"] = cl["Rows"].astype("int64")
cl["Correlation"] = cl["Correlation"].astype("float64")
cl["P Value"] = cl["P Value"].astype("float64")
wide = cl[cl["Group"] == "All"].pivot_table(index="Row Field", columns="Column Field", values="Correlation", aggfunc="first")
wide = wide.reindex(index=[f for f in fields if f in wide.index], columns=[f for f in fields if f in wide.columns]).reset_index().rename(columns={"Row Field": "Field"})
for c in wide.columns[1:]:
    wide[c] = wide[c].astype("float64")
wide.columns = [str(c) for c in wide.columns]
if not group_f:
    pr_df = pr_df.drop(columns=["Group"])
    cl = cl.drop(columns=["Group"])

omniscope_api.write_output(pr_df, "pairs")
omniscope_api.write_output(cl, "matrix")
omniscope_api.write_output(wide, "wide")
allp = pr_df if not group_f else pr_df[pr_df["Group"] == "All"]
top = allp.iloc[0] if len(allp) else None
omniscope_api.close(f"{len(pairs):,} pairs of {len(fields)} fields ({key})" + (f"; strongest: {top['Field A']} and {top['Field B']} ({top[key]:+.2f})" if top is not None and top[key] == top[key] else "")
                    + f"; {int((allp['Significant'] == 'Yes').sum()):,} significant at {alpha:g}.")
