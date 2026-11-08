"""Tiered Calculation: apply a tier table to an amount, the way commission
plans, tax bands, volume discounts, rebates and stepped tariffs work.

  MARGINAL  each slice of the amount is charged at its own tier's rate
            (like income tax bands or most commission accelerators)
  WHOLE     the whole amount is charged at the rate of the tier it falls in
            (like volume discount tables), plus that tier's fixed amount

Tiers come from a table on input 2 (from, to, rate, optional fixed amount and
an optional plan key so different rows can use different plans), or are typed
in the options ("0-10000: 0.02, 10000-50000: 0.05, 50000-: 0.08").
Each row gets the result, the effective rate and the tier reached; a second
output breaks the result down by tier.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


amt_f = opt("amount_field")
key_f = opt("plan_field")
mode = opt("mode", "MARGINAL")
tiers_txt = opt("tiers", "")
t_key, t_from, t_to, t_rate, t_fixed = opt("tier_plan_field"), opt("tier_from_field"), opt("tier_to_field"), opt("tier_rate_field"), opt("tier_fixed_field")
result_name = opt("result_name", "Tiered Result")

df = omniscope_api.read_input_records(input_number=0)
T = omniscope_api.read_input_records(input_number=1)
if df is None:
    omniscope_api.abort("Connect the amounts to input 1.")
if not amt_f or amt_f not in df.columns:
    omniscope_api.abort(f"Choose the amount field (got '{amt_f}').")
if key_f and key_f not in df.columns:
    omniscope_api.abort(f"Field '{key_f}' is not in input 1.")


def num(v):
    if v is None or pd.isna(v):
        return np.nan
    s = str(v).strip().replace(",", "").replace("£", "").replace("$", "")
    if s == "":
        return np.nan
    pct = s.endswith("%")
    try:
        x = float(s.rstrip("%"))
    except ValueError:
        return None
    return x / 100 if pct else x


plans = {}
if T is not None:
    for f, lab in ((t_from, "from"), (t_rate, "rate")):
        if not f or f not in T.columns:
            omniscope_api.abort(f"Choose the tier '{lab}' field of input 2.")
    for f in (t_key, t_to, t_fixed):
        if f and f not in T.columns:
            omniscope_api.abort(f"Field '{f}' is not in input 2.")
    for _, r in T.iterrows():
        k = str(r[t_key]).strip() if t_key and pd.notna(r[t_key]) else "*"
        lo, hi, rate = num(r[t_from]), num(r[t_to]) if t_to else np.nan, num(r[t_rate])
        fx = num(r[t_fixed]) if t_fixed else 0.0
        if lo is None or hi is None or rate is None or fx is None or lo != lo or rate != rate:
            omniscope_api.abort(f"Tier row for plan '{k}' has a value that is not a number (from {r[t_from]}, rate {r[t_rate]}).")
        plans.setdefault(k, []).append([lo, hi, rate, 0.0 if fx != fx else fx])
else:
    for part in [p.strip() for p in re.split(r"[,;\n]", tiers_txt or "") if p.strip()]:
        m = re.match(r"^\s*([\d.]+)\s*-\s*([\d.]*)\s*:\s*([\d.]+%?)\s*(?:\+\s*([\d.]+))?\s*$", part)
        if not m:
            omniscope_api.abort(f"Could not read the tier '{part}'. Use from-to: rate, for example 0-10000: 0.02 (leave 'to' empty for the top tier).")
        plans.setdefault("*", []).append([float(m.group(1)), float(m.group(2)) if m.group(2) else np.nan, num(m.group(3)), float(m.group(4) or 0)])
if not plans:
    omniscope_api.abort("Give the tiers: connect a tier table to input 2, or type them in the options.")
for k, tl in plans.items():
    tl.sort(key=lambda x: x[0])
    for i, t in enumerate(tl):
        if t[1] != t[1]:
            t[1] = tl[i + 1][0] if i + 1 < len(tl) else np.inf  # "to" defaults to the next tier's "from"
        if t[1] <= t[0]:
            omniscope_api.abort(f"Plan '{k}': tier from {t[0]:g} to {t[1]:g} is empty or reversed.")
        if i and t[0] < tl[i - 1][1] - 1e-9:
            omniscope_api.abort(f"Plan '{k}': tiers overlap at {t[0]:g}.")

amounts = pd.to_numeric(df[amt_f], errors="coerce").astype("float64").to_numpy()
keys = df[key_f].astype(object).map(lambda v: str(v).strip() if v is not None and v == v else None).tolist() if key_f else ["*"] * len(df)
res = np.full(len(df), np.nan)
reached = [None] * len(df)
brows = []
missing_plan = set()
for i, (a, k) in enumerate(zip(amounts, keys)):
    tl = plans.get(k) if k in plans else plans.get("*") if "*" in plans and key_f is None else plans.get(k)
    if tl is None:
        tl = plans.get("*")
    if tl is None:
        missing_plan.add(k)
        continue
    if a != a:
        continue
    total = 0.0
    for n, (lo, hi, rate, fx) in enumerate(tl, start=1):
        label = f"{lo:,.0f} to {hi:,.0f}" if np.isfinite(hi) else f"{lo:,.0f} and over"
        if mode == "MARGINAL":
            part = max(0.0, min(a, hi) - lo)
            if part <= 0:
                continue
            val = part * rate + (fx if a >= lo else 0.0)
            total += val
            reached[i] = label
            brows.append((i + 1, k, n, label, rate, part, val))
        else:
            if lo <= a < hi or (not np.isfinite(hi) and a >= lo):
                total = a * rate + fx
                reached[i] = label
                brows.append((i + 1, k, n, label, rate, a, total))
    res[i] = total
out = df.copy()
out[result_name] = res
out["Effective Rate"] = np.where((amounts != 0) & ~np.isnan(res), res / np.where(amounts != 0, amounts, 1), np.nan)
out["Tier Reached"] = reached
for c in (result_name, "Effective Rate"):
    out[c] = out[c].astype("float64")
br = pd.DataFrame(brows, columns=["Row Number", "Plan", "Tier", "Band", "Rate", "Amount In Tier", "Result In Tier"])
br["Row Number"] = br["Row Number"].astype("int64")
br["Tier"] = br["Tier"].astype("int64")
for c in ("Rate", "Amount In Tier", "Result In Tier"):
    br[c] = br[c].astype("float64")
if not key_f and set(br["Plan"]) <= {"*"}:
    br = br.drop(columns=["Plan"])
omniscope_api.write_output(out, "rows")
omniscope_api.write_output(br, "breakdown")
omniscope_api.close(f"{int((~np.isnan(res)).sum()):,} of {len(out):,} rows calculated ({mode.lower()} tiers); total {np.nansum(res):,.2f}"
                    + (f"; no tiers for plan(s): {', '.join(sorted(str(x) for x in missing_plan))[:200]}" if missing_plan else "") + ".")
