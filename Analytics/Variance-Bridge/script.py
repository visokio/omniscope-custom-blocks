"""Variance Bridge: explain the difference between two totals (budget and
actual, last year and this year, forecast and outturn) as a waterfall of
category variances, ready for a bridge chart.

Values are summed per category; categories are ordered by the size of their
variance (or by name), small ones can be grouped into "Other", and each step
carries its bar start and end for a waterfall chart. Variances are labelled
favourable or adverse: higher is better for revenue-like measures, lower is
better for costs. Optionally one bridge per group (region, business unit).
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


cat_f, base_f, cur_f = opt("category_field"), opt("base_field"), opt("current_field")
group_f = opt("group_field")
base_label, cur_label = opt("base_label", "Budget"), opt("current_label", "Actual")
better = opt("better_when", "HIGHER")
order = opt("order", "SIZE")
top_n = int(opt("top_n", 0) or 0)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
for f, lab in ((cat_f, "category"), (base_f, "base value"), (cur_f, "current value")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
if group_f and group_f not in df.columns:
    omniscope_api.abort(f"Field '{group_f}' is not in the input.")
w = pd.DataFrame({"c": df[cat_f].astype(object).where(df[cat_f].notna(), "(blank)").map(str),
                  "b": pd.to_numeric(df[base_f], errors="coerce").fillna(0).astype("float64"),
                  "a": pd.to_numeric(df[cur_f], errors="coerce").fillna(0).astype("float64"),
                  "g": df[group_f].astype(object).where(df[group_f].notna(), "(blank)").map(str) if group_f else "All"})
rows, crows = [], []
for g, d in w.groupby("g", sort=True):
    t = d.groupby("c", sort=False)[["b", "a"]].sum()
    t["v"] = t["a"] - t["b"]
    t = t.sort_values("v", key=lambda s: -s.abs(), kind="mergesort") if order == "SIZE" else t.sort_index()
    if top_n and len(t) > top_n:
        keep = t.iloc[:top_n]
        rest = t.iloc[top_n:]
        t = pd.concat([keep, pd.DataFrame({"b": [rest["b"].sum()], "a": [rest["a"].sum()], "v": [rest["v"].sum()]}, index=[f"Other ({len(rest)})"])])
    B, A = float(d["b"].sum()), float(d["a"].sum())
    steps = [(base_label, B, "Total")] + [(c, float(r["v"]), "Variance") for c, r in t.iterrows()] + [(cur_label, A, "Total")]
    run_ = B
    for i, (lab, val, kind) in enumerate(steps, start=1):
        if kind == "Total":
            start, end = 0.0, val
        else:
            start, end = run_, run_ + val
            run_ = end
        fav = None if kind == "Total" or val == 0 else ("Favourable" if (val > 0) == (better == "HIGHER") else "Adverse")
        rows.append({"Group": g, "Step": i, "Label": lab, "Kind": kind, "Value": val, "Bar Start": start, "Bar End": end, "Direction": fav,
                     "Share Of Total Variance": (val / (A - B)) if kind == "Variance" and A != B else np.nan})
    for c, r in t.iterrows():
        crows.append({"Group": g, "Category": c, base_label: float(r["b"]), cur_label: float(r["a"]), "Variance": float(r["v"]),
                      "Variance %": float(r["v"] / r["b"]) if r["b"] else np.nan,
                      "Direction": None if r["v"] == 0 else ("Favourable" if (r["v"] > 0) == (better == "HIGHER") else "Adverse")})
br = pd.DataFrame(rows, columns=["Group", "Step", "Label", "Kind", "Value", "Bar Start", "Bar End", "Direction", "Share Of Total Variance"])
ct = pd.DataFrame(crows, columns=["Group", "Category", base_label, cur_label, "Variance", "Variance %", "Direction"])
br["Step"] = br["Step"].astype("int64")
for c in ("Value", "Bar Start", "Bar End", "Share Of Total Variance"):
    br[c] = br[c].astype("float64")
for c in (base_label, cur_label, "Variance", "Variance %"):
    ct[c] = ct[c].astype("float64")
for t_ in (br, ct):
    if group_f:
        t_.rename(columns={"Group": str(group_f)}, inplace=True)
    else:
        t_.drop(columns=["Group"], inplace=True)
omniscope_api.write_output(br, "bridge")
omniscope_api.write_output(ct, "categories")
tot = ct["Variance"].sum() if len(ct) else 0.0
omniscope_api.close(f"{len(ct):,} category rows; total variance {tot:+,.2f} ({cur_label} vs {base_label})" + (f", {w['g'].nunique()} bridges" if group_f else "") + ".")
