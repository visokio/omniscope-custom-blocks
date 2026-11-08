"""Weighted Scoring: multi-criteria scorecards for choosing between suppliers,
sites, bids, projects or candidates.

Each criterion is put on a 0-100 scale (min-max, percent of best, rank or
z-score), turned round where lower is better (price, distance, risk), multiplied
by its weight and summed to a 0-100 total. Alternatives are ranked (within
groups if chosen), optional pass / fail thresholds knock out alternatives that
miss a minimum or exceed a maximum, and a sensitivity check reports how far
each weight would have to move to change the winner.

Weights come from the options ("Price: 30, Quality: 25, ...") or from an
optional second input with one row per criterion (criterion, weight,
direction, minimum, maximum).
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


name_f = opt("name_field")
crit = list(opt("criteria_fields", []) or [])
weights_txt = opt("weights", "")
lower_better = set(opt("lower_better_fields", []) or [])
group_fields = list(opt("group_fields", []) or [])
method = opt("method", "MIN_MAX")
missing = opt("missing", "WORST")
c_name = opt("crit_name_field")
c_weight = opt("crit_weight_field")
c_dir = opt("crit_direction_field")
c_min = opt("crit_min_field")
c_max = opt("crit_max_field")

df = omniscope_api.read_input_records(input_number=0)
cdf = omniscope_api.read_input_records(input_number=1)
if df is None:
    omniscope_api.abort("Connect the alternatives (one row per supplier, site, bid...) to input 1.")
if not name_f or name_f not in df.columns:
    omniscope_api.abort(f"Choose the name field (got '{name_f}').")
miss = [f for f in group_fields if f not in df.columns]
if miss:
    omniscope_api.abort(f"Group fields not in the input: {', '.join(miss)}")

# ---- criteria definitions
defs = {}  # name -> dict(weight, lower, min, max)
if cdf is not None:
    for f, lab in ((c_name, "criterion name"), (c_weight, "weight")):
        if not f or f not in cdf.columns:
            omniscope_api.abort(f"Choose the {lab} field of the criteria input (input 2).")
    for f in (c_dir, c_min, c_max):
        if f and f not in cdf.columns:
            omniscope_api.abort(f"Field '{f}' is not in the criteria input.")
    for _, r in cdf.iterrows():
        nm = str(r[c_name]).strip()
        if nm not in df.columns:
            omniscope_api.abort(f"Criterion '{nm}' from input 2 is not a field of input 1.")
        wv = pd.to_numeric(pd.Series([r[c_weight]]), errors="coerce").iloc[0]
        if pd.isna(wv) or wv < 0:
            omniscope_api.abort(f"Criterion '{nm}' needs a weight of 0 or more.")
        dtxt = str(r[c_dir]).strip().lower() if c_dir and pd.notna(r[c_dir]) else ""
        lo = dtxt.startswith(("low", "min", "less", "smaller", "-")) or nm in lower_better
        mn = pd.to_numeric(pd.Series([r[c_min]]), errors="coerce").iloc[0] if c_min else np.nan
        mx = pd.to_numeric(pd.Series([r[c_max]]), errors="coerce").iloc[0] if c_max else np.nan
        defs[nm] = {"weight": float(wv), "lower": lo, "min": mn, "max": mx}
else:
    if not crit:
        omniscope_api.abort("Choose the criteria fields, or connect a criteria table to input 2.")
    miss = [c for c in crit if c not in df.columns]
    if miss:
        omniscope_api.abort(f"Criteria fields not in the input: {', '.join(miss)}")
    w_named, w_list = {}, []
    for part in [p.strip() for p in re.split(r"[,;\n]", weights_txt or "") if p.strip()]:
        m = re.match(r"^(.*?)\s*[:=]\s*(-?[\d.]+)\s*%?$", part)
        if m:
            w_named[m.group(1).strip().lower()] = float(m.group(2))
        else:
            try:
                w_list.append(float(part.rstrip("%")))
            except ValueError:
                omniscope_api.abort(f"Could not read the weight '{part}'. Use 'Field: weight' pairs or numbers in criteria order.")
    if w_list and len(w_list) != len(crit):
        omniscope_api.abort(f"{len(w_list)} weights given for {len(crit)} criteria; give one per criterion, in order.")
    for i, c in enumerate(crit):
        wv = w_named.get(c.lower(), w_list[i] if w_list else (np.nan if w_named else 1.0))
        if wv != wv:
            omniscope_api.abort(f"No weight given for '{c}'.")
        if wv < 0:
            omniscope_api.abort(f"Weight for '{c}' must be 0 or more.")
        defs[c] = {"weight": float(wv), "lower": c in lower_better, "min": np.nan, "max": np.nan}
    unknown = set(w_named) - {c.lower() for c in crit}
    if unknown:
        omniscope_api.abort(f"Weights given for fields that are not chosen criteria: {', '.join(sorted(unknown))}")
crit = list(defs)
W = np.array([defs[c]["weight"] for c in crit], dtype=float)
if W.sum() <= 0:
    omniscope_api.abort("At least one weight must be above zero.")
Wn = W / W.sum()

X = pd.DataFrame({c: pd.to_numeric(df[c], errors="coerce").astype("float64") for c in crit}, index=df.index)
bad = [c for c in crit if df[c].notna().any() and X[c].isna().all()]
if bad:
    omniscope_api.abort(f"Criteria must be numeric: {', '.join(bad)}")
for g in group_fields:
    df[g] = df[g].astype(object).where(df[g].notna(), "(blank)")


fails = [[] for _ in range(len(df))]
for j, c in enumerate(crit):
    mn, mx = defs[c]["min"], defs[c]["max"]
    xv = X[c].to_numpy()
    for i in range(len(df)):
        if mn == mn and not (xv[i] >= mn):
            fails[i].append(f"{c} below {mn:g}")
        if mx == mx and not (xv[i] <= mx):
            fails[i].append(f"{c} above {mx:g}")
passes = pd.Series([len(f) == 0 for f in fails], index=df.index)


def normalise(col, lower, ref):
    """0-100 score; the scale comes from the alternatives that pass the thresholds (ref), others are clipped to it."""
    v = -col if lower else col
    r = v[ref & v.notna()]
    if len(r) == 0:
        r = v.dropna()
    if len(r) == 0:
        return v * np.nan
    if method == "MIN_MAX":
        lo, hi = r.min(), r.max()
        out = (v - lo) / (hi - lo) * 100 if hi > lo else v * 0 + 100.0
    elif method == "PERCENT_OF_BEST":
        c, rc = col, col[r.index]
        if lower:
            best = rc[rc > 0].min() if (rc > 0).any() else np.nan
            out = (best / c * 100).where(c > 0, 0.0) if best == best else c * 0
        else:
            best = rc.max()
            out = c / best * 100 if best > 0 else c * 0
    elif method == "RANK":
        rv = np.sort(r.to_numpy())
        n = len(rv)
        below = np.searchsorted(rv, v.to_numpy(), side="left")
        equal = np.searchsorted(rv, v.to_numpy(), side="right") - below
        pos = below + np.maximum(equal - 1, 0) / 2.0
        out = pd.Series(np.where(v.notna(), pos / (n - 1) * 100 if n > 1 else 100.0, np.nan), index=v.index)
    else:
        sd = r.std(ddof=0)
        z = (v - r.mean()) / sd if sd > 0 else v * 0
        out = 50 + 50 * z / 3  # z-score mapped so +-3 sd spans 0..100
    return out.clip(0, 100)


groups = [((), df.index)] if not group_fields else [((k if isinstance(k, tuple) else (k,)), g.index) for k, g in df.groupby(group_fields, sort=True)]
S = pd.DataFrame(index=df.index, columns=crit, dtype="float64")
for _, idx in groups:
    for c in crit:
        S.loc[idx, c] = normalise(X.loc[idx, c], defs[c]["lower"], passes.loc[idx]).to_numpy()
avail = S.notna()
if missing == "WORST":
    Sf = S.fillna(0.0)
    total = Sf.to_numpy() @ Wn
elif missing == "AVERAGE":
    Sf = S.fillna(50.0)
    total = Sf.to_numpy() @ Wn
else:  # REWEIGHT across the criteria the alternative has
    Sf = S.fillna(0.0)
    wa = avail.to_numpy() * Wn
    total = np.where(wa.sum(axis=1) > 0, (Sf.to_numpy() * wa).sum(axis=1) / np.where(wa.sum(axis=1) > 0, wa.sum(axis=1), 1), np.nan)
if missing == "REWEIGHT":
    wa = avail.to_numpy() * Wn
    contrib = Sf.to_numpy() * wa / np.where(wa.sum(axis=1, keepdims=True) > 0, wa.sum(axis=1, keepdims=True), 1)
else:
    contrib = Sf.to_numpy() * Wn

out = df[[name_f] + group_fields].copy()
for j, c in enumerate(crit):
    out[f"{c} Score"] = S[c].to_numpy()
for j, c in enumerate(crit):
    out[f"{c} Points"] = contrib[:, j]
out["Total Score"] = total
out["Criteria Missing"] = (~avail).sum(axis=1).astype("int64").to_numpy()
out["Passes Thresholds"] = np.where([len(f) == 0 for f in fails], "Yes", "No")
out["Failed On"] = ["; ".join(f) for f in fails]
out["Rank"] = pd.array([pd.NA] * len(out), dtype="Int64")
out["Gap To Leader"] = np.nan
out["Leader"] = "No"
for _, idx in groups:
    sub = out.loc[idx]
    ok = sub["Passes Thresholds"] == "Yes"
    rk = sub["Total Score"].where(ok).rank(ascending=False, method="min")
    out.loc[idx, "Rank"] = pd.array(rk.to_numpy(), dtype="Float64").astype("Int64")
    if ok.any() and sub.loc[ok, "Total Score"].notna().any():
        best = sub.loc[ok, "Total Score"].max()
        out.loc[idx, "Gap To Leader"] = (best - sub["Total Score"]).where(ok).to_numpy()
        out.loc[idx, "Leader"] = np.where((rk == 1).to_numpy(), "Yes", "No")
out["Gap To Leader"] = out["Gap To Leader"].astype("float64")
out["Total Score"] = out["Total Score"].astype("float64")
for c in crit:
    out[f"{c} Score"] = out[f"{c} Score"].astype("float64")
    out[f"{c} Points"] = out[f"{c} Points"].astype("float64")
out = out.sort_values(group_fields + ["Rank", "Total Score"], ascending=[True] * len(group_fields) + [True, False], na_position="last", kind="mergesort").reset_index(drop=True)


# ---- sensitivity: how far does each weight have to move to change the leader
def leader_for(wvec, idx, ok_mask):
    tot = Sf.loc[idx].to_numpy() @ (wvec / wvec.sum())
    tot = np.where(ok_mask, tot, -np.inf)
    return int(np.argmax(tot)) if np.isfinite(tot).any() else -1


crit_rows = []
for key, idx in groups:
    gd = dict(zip(group_fields, key))
    ok_mask = np.array([len(fails[df.index.get_loc(i)]) == 0 for i in idx])
    names = df.loc[idx, name_f].astype(str).to_numpy()
    base = leader_for(Wn, idx, ok_mask) if len(idx) else -1
    for j, c in enumerate(crit):
        found_lo, found_hi = None, None
        if base >= 0 and missing != "REWEIGHT":
            for step in np.arange(0.005, 1.0001, 0.005):
                for sign in (-1, 1):
                    nw = Wn[j] + sign * step
                    if nw < 0 or nw > 1 or (sign < 0 and found_lo is not None) or (sign > 0 and found_hi is not None):
                        continue
                    rest = 1 - Wn[j]
                    wv = Wn * ((1 - nw) / rest) if rest > 0 else np.zeros_like(Wn)
                    wv[j] = nw
                    if wv.sum() <= 0:
                        continue
                    lw = leader_for(wv, idx, ok_mask)
                    if lw != base:
                        if sign < 0:
                            found_lo = (nw, names[lw])
                        else:
                            found_hi = (nw, names[lw])
                if found_lo is not None and found_hi is not None:
                    break
        cand = [f for f in (found_lo, found_hi) if f is not None]
        near = min(cand, key=lambda f: abs(f[0] - Wn[j])) if cand else None
        crit_rows.append({**gd, "Criterion": c, "Weight": W[j], "Weight Share": Wn[j], "Better When": "Lower" if defs[c]["lower"] else "Higher",
                          "Minimum": defs[c]["min"], "Maximum": defs[c]["max"], "Average Raw Value": float(X.loc[idx, c].mean()) if len(idx) else np.nan,
                          "Average Points": float(contrib[[df.index.get_loc(i) for i in idx], j].mean()) if len(idx) else np.nan,
                          "Leader": names[base] if base >= 0 else None,
                          "Weight Share That Changes Leader": near[0] if near else np.nan,
                          "New Leader": near[1] if near else None,
                          "Weight Change Needed (points)": 100 * (near[0] - Wn[j]) if near else np.nan,
                          "Sensitivity": ("" if base < 0 or missing == "REWEIGHT" else
                                          f"{names[base]} leads at any weight for this criterion" if not near else
                                          f"Leader changes to {near[1]} if the weight {'rises' if near[0] > Wn[j] else 'falls'} to {near[0]:.1%} ({100 * (near[0] - Wn[j]):+.1f} points)")})
cols = group_fields + ["Criterion", "Weight", "Weight Share", "Better When", "Minimum", "Maximum", "Average Raw Value", "Average Points", "Leader",
                       "Weight Share That Changes Leader", "New Leader", "Weight Change Needed (points)", "Sensitivity"]
cr = pd.DataFrame(crit_rows, columns=cols)
cr["Sensitivity"] = cr["Sensitivity"].replace("", None)
for c in ("Weight", "Weight Share", "Minimum", "Maximum", "Average Raw Value", "Average Points", "Weight Share That Changes Leader", "Weight Change Needed (points)"):
    cr[c] = cr[c].astype("float64")

long = out.melt(id_vars=[name_f] + group_fields + ["Total Score", "Rank"], value_vars=[f"{c} Points" for c in crit], var_name="Criterion", value_name="Points")
long["Criterion"] = long["Criterion"].str.slice(0, -len(" Points"))
long["Points"] = long["Points"].astype("float64")

omniscope_api.write_output(out, "scores")
omniscope_api.write_output(cr, "criteria")
omniscope_api.write_output(long, "contributions")
lead = out[out["Leader"] == "Yes"]
knocked = int((out["Passes Thresholds"] == "No").sum())
msg = f"{len(out):,} alternatives scored on {len(crit)} criteria"
if not group_fields and len(lead):
    msg += f"; leader: {lead.iloc[0][name_f]} ({lead.iloc[0]['Total Score']:.1f})"
omniscope_api.close(msg + (f"; {knocked:,} failed a threshold" if knocked else "") + ".")
