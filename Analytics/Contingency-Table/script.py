"""Contingency Table and Chi-square: cross-tabulate two categorical fields and
test whether they are associated.

Output 1 (one row per cell): count, row / column / total share, expected count,
adjusted standardised residual (which cells drive the association, |r| > 1.96
is notable), contribution to chi-square.
Output 2 (one row per table, or per segment): chi-square, degrees of freedom,
p-value, Cramer's V, sample size, smallest expected count and a verdict.
Optional weight field (pre-aggregated counts) and segments. Pure Python.
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


row_field = opt("row_field")
col_field = opt("col_field")
weight_field = opt("weight_field")
segment_fields = opt("segment_fields", []) or []
yates = opt("yates", False)
alpha = float(opt("alpha", 0.05))
include_blank = opt("include_blank", False)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
for f, label in ((row_field, "row"), (col_field, "column")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
if row_field == col_field:
    omniscope_api.abort("Choose two different fields for rows and columns.")
for f in [weight_field] + list(segment_fields):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")


def gammaincc(a, x):
    """Regularised upper incomplete gamma Q(a, x) (Numerical Recipes)."""
    if x <= 0:
        return 1.0
    gln = math.lgamma(a)
    if x < a + 1:
        ap, s = a, 1.0 / a
        d = s
        for _ in range(1000):
            ap += 1
            d *= x / ap
            s += d
            if abs(d) < abs(s) * 1e-15:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - gln)
    b = x + 1 - a
    c, d = 1e300, 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = b + an / c
        c = c if abs(c) > 1e-300 else 1e-300
        de = d * c
        h *= de
        if abs(de - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def label(v):
    if v is None or (isinstance(v, float) and v != v):
        return "(blank)"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


w = df.copy()
w["__r"] = w[row_field].map(label)
w["__c"] = w[col_field].map(label)
w["__w"] = pd.to_numeric(w[weight_field], errors="coerce").fillna(0.0) if weight_field else 1.0
if not include_blank:
    w = w[(w["__r"] != "(blank)") & (w["__c"] != "(blank)")]

if segment_fields:
    keys = [w[c].map(label) for c in segment_fields]
    segs = [((k if isinstance(k, tuple) else (k,)), g) for k, g in w.groupby(keys, sort=True)]
else:
    segs = [((), w)]

cells, tests = [], []
for seg, g in segs:
    sd = {c: seg[i] for i, c in enumerate(segment_fields)}
    tab = g.pivot_table(index="__r", columns="__c", values="__w", aggfunc="sum", fill_value=0.0)
    tab = tab.sort_index().reindex(sorted(tab.columns), axis=1)
    O = tab.to_numpy(dtype=float)
    n = O.sum()
    r, c = O.shape if O.size else (0, 0)
    if n <= 0 or r < 2 or c < 2:
        tests.append({**sd, "Rows": r, "Columns": c, "Sample Size": n, "Chi-Square": np.nan, "Degrees Of Freedom": max(0, (r - 1) * (c - 1)),
                      "P Value": np.nan, "Cramer's V": np.nan, "Smallest Expected Count": np.nan, "Cells Expected Below 5": 0,
                      "Verdict": "Need at least two rows and two columns with data."})
        continue
    rs, cs = O.sum(axis=1, keepdims=True), O.sum(axis=0, keepdims=True)
    E = rs @ cs / n
    with np.errstate(divide="ignore", invalid="ignore"):
        if yates and r == 2 and c == 2:
            contrib = (np.maximum(np.abs(O - E) - 0.5, 0) ** 2) / E
        else:
            contrib = (O - E) ** 2 / E
        contrib = np.nan_to_num(contrib)
        adj = (O - E) / np.sqrt(E * (1 - rs / n) * (1 - cs / n))
    chi = float(contrib.sum())
    dof = (r - 1) * (c - 1)
    p = gammaincc(dof / 2, chi / 2)
    v = math.sqrt(chi / (n * min(r - 1, c - 1))) if n and min(r, c) > 1 else np.nan
    low = int((E < 5).sum())
    strength = "negligible" if v < 0.1 else "weak" if v < 0.2 else "moderate" if v < 0.4 else "strong"
    if p < alpha:
        i, j = np.unravel_index(np.nanargmax(adj), adj.shape)
        verdict = (f"{row_field} and {col_field} are associated (p = {p:.3g}, Cramer's V = {v:.2f}, {strength}). "
                   f"Most over-represented: {tab.index[i]} with {tab.columns[j]}.")
    else:
        verdict = f"No significant association between {row_field} and {col_field} (p = {p:.3g})."
    if low:
        verdict += f" Caution: {low} cell(s) have an expected count below 5."
    tests.append({**sd, "Rows": r, "Columns": c, "Sample Size": n, "Chi-Square": chi, "Degrees Of Freedom": dof, "P Value": p,
                  "Cramer's V": v, "Smallest Expected Count": float(E.min()), "Cells Expected Below 5": low, "Verdict": verdict})
    for i, rv in enumerate(tab.index):
        for j, cv in enumerate(tab.columns):
            cells.append({**sd, str(row_field): rv, str(col_field): cv, "Count": O[i, j], "Row Share": O[i, j] / rs[i, 0] if rs[i, 0] else np.nan,
                          "Column Share": O[i, j] / cs[0, j] if cs[0, j] else np.nan, "Share Of Total": O[i, j] / n,
                          "Expected Count": E[i, j], "Adjusted Residual": adj[i, j], "Chi-Square Contribution": contrib[i, j],
                          "Notable": ("Over-represented" if adj[i, j] > 1.96 else "Under-represented" if adj[i, j] < -1.96 else "")})

cell_cols = list(segment_fields) + [str(row_field), str(col_field), "Count", "Row Share", "Column Share", "Share Of Total", "Expected Count",
                                    "Adjusted Residual", "Chi-Square Contribution", "Notable"]
cdf = pd.DataFrame(cells, columns=cell_cols)
for cc in cell_cols[len(segment_fields) + 2:-1]:
    cdf[cc] = cdf[cc].astype("float64")
if not weight_field and len(cdf):
    cdf["Count"] = cdf["Count"].round().astype("int64")
tcols = list(segment_fields) + ["Rows", "Columns", "Sample Size", "Chi-Square", "Degrees Of Freedom", "P Value", "Cramer's V",
                                "Smallest Expected Count", "Cells Expected Below 5", "Verdict"]
tdf = pd.DataFrame(tests, columns=tcols)
for cc in ("Rows", "Columns", "Degrees Of Freedom", "Cells Expected Below 5"):
    tdf[cc] = tdf[cc].astype("int64")
for cc in ("Sample Size", "Chi-Square", "P Value", "Cramer's V", "Smallest Expected Count"):
    tdf[cc] = tdf[cc].astype("float64")

omniscope_api.write_output(cdf, "cells")
omniscope_api.write_output(tdf, "test")
sig = int((tdf["P Value"] < alpha).sum())
omniscope_api.close(f"{len(tdf)} table(s) tested; {sig} with a significant association at {alpha:g}.")
