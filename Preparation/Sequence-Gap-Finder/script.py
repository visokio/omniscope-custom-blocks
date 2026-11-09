"""Sequence Gap Finder: check numbered documents (invoices, credit notes,
cheques, purchase orders, tickets) for missing numbers, duplicates and numbers
issued out of date order, per series, the completeness test auditors run.

Numbers can carry a prefix ("INV-000123"): the digits at the end are the
sequence number and the rest is the series, unless a series field is given.
Outputs: one row per gap (from, to, how many missing), one row per problem
document (duplicate or out of order), and a summary per series.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


num_f, series_f, date_f = opt("number_field"), opt("series_field"), opt("date_field")
max_list = int(opt("max_missing_listed", 20))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the documents to the input.")
if not num_f or num_f not in df.columns:
    omniscope_api.abort(f"Choose the document number field (got '{num_f}').")
for f in (series_f, date_f):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")
RX = re.compile(r"^(.*?)(\d+)\s*$")
raw = df[num_f].astype(object).map(lambda v: None if v is None or (isinstance(v, float) and v != v) else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).strip()))
parsed = raw.map(lambda v: RX.match(v) if isinstance(v, str) and v else None)
w = pd.DataFrame({"row": np.arange(len(df)) + 1, "doc": raw,
                  "series": (df[series_f].astype(object).where(df[series_f].notna(), "(blank)").map(str) if series_f else parsed.map(lambda m: m.group(1) if m else None)),
                  "n": parsed.map(lambda m: int(m.group(2)) if m else None), "width": parsed.map(lambda m: len(m.group(2)) if m else None)})
if date_f:
    d = df[date_f]
    w["date"] = (d.dt.tz_localize(None) if pd.api.types.is_datetime64_any_dtype(d) and d.dt.tz is not None else pd.to_datetime(d, errors="coerce", format="mixed")).to_numpy()
unparsed = int(w["n"].isna().sum())
w = w.dropna(subset=["n"])
w["n"] = w["n"].astype("int64")
grows, prows, srows = [], [], []
for s, g in w.groupby("series", sort=True):
    nums = np.sort(g["n"].unique())
    width = int(g["width"].mode().iloc[0])
    fmt = lambda k: f"{s}{k:0{width}d}"
    missing_total = 0
    for a, b in zip(nums[:-1], nums[1:]):
        if b - a > 1:
            cnt = int(b - a - 1)
            missing_total += cnt
            listed = ", ".join(fmt(k) for k in range(a + 1, min(b, a + 1 + max_list)))
            grows.append({"Series": s, "Last Before Gap": fmt(a), "First After Gap": fmt(b), "Missing Count": cnt,
                          "Missing Numbers": listed + (", ..." if cnt > max_list else "")})
    dup = g[g.duplicated("n", keep=False)]
    for _, r in dup.iterrows():
        prows.append({"Series": s, "Document": r["doc"], "Row Number": int(r["row"]), "Problem": "Duplicate number", "Detail": f"{int((g['n'] == r['n']).sum())} rows share this number"})
    ooo = 0
    if date_f:
        gg = g.dropna(subset=["date"]).sort_values(["n", "row"])
        running = gg["date"].cummax()
        bad = gg[gg["date"] < running.shift(1)]
        for _, r in bad.iterrows():
            ooo += 1
            prev = gg[(gg["n"] < r["n"]) & (gg["date"] > r["date"])].iloc[-1]
            prows.append({"Series": s, "Document": r["doc"], "Row Number": int(r["row"]), "Problem": "Dated before an earlier number",
                          "Detail": f"dated {pd.Timestamp(r['date']).date()}, but {prev['doc']} is dated {pd.Timestamp(prev['date']).date()}"})
    span = int(nums[-1] - nums[0] + 1)
    srows.append({"Series": s, "Documents": int(len(g)), "First Number": fmt(nums[0]), "Last Number": fmt(nums[-1]), "Expected In Range": span,
                  "Missing": missing_total, "Gaps": sum(1 for gr in grows if gr["Series"] == s), "Duplicate Rows": int(len(dup)),
                  "Out Of Order": ooo, "Completeness": (span - missing_total) / span if span else np.nan})
gaps = pd.DataFrame(grows, columns=["Series", "Last Before Gap", "First After Gap", "Missing Count", "Missing Numbers"])
gaps["Missing Count"] = gaps["Missing Count"].astype("int64")
probs = pd.DataFrame(prows, columns=["Series", "Document", "Row Number", "Problem", "Detail"])
probs["Row Number"] = probs["Row Number"].astype("int64")
summ = pd.DataFrame(srows, columns=["Series", "Documents", "First Number", "Last Number", "Expected In Range", "Missing", "Gaps", "Duplicate Rows", "Out Of Order", "Completeness"])
for c in ("Documents", "Expected In Range", "Missing", "Gaps", "Duplicate Rows", "Out Of Order"):
    summ[c] = summ[c].astype("int64")
summ["Completeness"] = summ["Completeness"].astype("float64")
omniscope_api.write_output(gaps, "gaps")
omniscope_api.write_output(probs, "problems")
omniscope_api.write_output(summ, "summary")
omniscope_api.close(f"{len(summ)} series, {len(w):,} numbered documents: {int(summ['Missing'].sum()):,} numbers missing in {len(gaps):,} gaps, "
                    f"{int(summ['Duplicate Rows'].sum()):,} duplicate rows, {int(summ['Out Of Order'].sum()):,} out of date order"
                    + (f"; {unparsed:,} values without a number skipped" if unparsed else "") + ".")
