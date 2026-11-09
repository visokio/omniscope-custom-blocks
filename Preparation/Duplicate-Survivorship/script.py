"""Duplicate Survivorship: find duplicate records within one dataset and keep
the best one of each group (the "survivor"), the way data stewards
de-duplicate customer, supplier or product masters.

  Duplicates: records whose match fields agree after normalising (case,
  spaces, punctuation; optional digits-only for phone numbers), on one or more
  match keys tried in order (for example email, then name + postcode). Records
  linked by any key end up in the same group.
  Survivor: chosen by rules in order: most complete record, latest or earliest
  date, highest or lowest value, then first in the input.
  Optionally fills gaps in the survivor from the other records in its group.

Outputs: every record with group ID, group size, survivor flag and the key
that linked it; the survivors only (the de-duplicated table); and the groups.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


keys_txt = opt("match_keys", "")
digits_only = list(opt("digits_only_fields", []) or [])
rule = opt("survivor_rule", "COMPLETE")
rule_f = opt("rule_field")
fill = bool(opt("fill_gaps", True))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the records to the input.")
keys = []
for part in [p.strip() for p in re.split(r"[;\n]", keys_txt or "") if p.strip()]:
    fs = [f.strip() for f in part.split("+") if f.strip()]
    miss = [f for f in fs if f not in df.columns]
    if miss:
        omniscope_api.abort(f"Match key '{part}': fields not in the input: {', '.join(miss)}")
    keys.append(fs)
if not keys:
    omniscope_api.abort("Give at least one match key, for example: Email; Last Name + Postcode (keys separated by ';', fields within a key by '+').")
if rule in ("LATEST", "EARLIEST", "HIGHEST", "LOWEST") and (not rule_f or rule_f not in df.columns):
    omniscope_api.abort("Choose the field the survivor rule uses (a date for latest / earliest, a number for highest / lowest).")
df = df.reset_index(drop=True)
n = len(df)


def norm(col):
    s = df[col].astype(object).where(df[col].notna(), None)
    if col in digits_only:
        return s.map(lambda v: None if v is None else (re.sub(r"\D", "", str(v)) or None))
    return s.map(lambda v: None if v is None else (re.sub(r"[^0-9a-z]+", "", str(v).lower()) or None))


normed = {c: norm(c) for k in keys for c in k}
parent = np.arange(n)


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


linked_by = [None] * n
for k in keys:
    kv = pd.concat([normed[c] for c in k], axis=1)
    ok = kv.notna().all(axis=1).to_numpy()
    if not ok.any():
        continue
    joined = kv[ok].astype(str).agg("\u0001".join, axis=1)
    for _, idx in joined.groupby(joined).groups.items():
        idx = list(idx)
        if len(idx) < 2:
            continue
        r0 = find(idx[0])
        for i in idx[1:]:
            ri = find(i)
            if ri != r0:
                parent[ri] = r0
        for i in idx:
            if linked_by[i] is None:
                linked_by[i] = " + ".join(k)
roots = np.array([find(i) for i in range(n)])
_, gid = np.unique(roots, return_inverse=True) if n else (None, np.array([], dtype=int))
gsize = np.bincount(gid)[gid] if n else np.array([], dtype=int)
filled = df.notna() & (df.astype(str).apply(lambda c: c.str.strip()) != "")
completeness = filled.sum(axis=1).to_numpy()
if rule in ("LATEST", "EARLIEST"):
    rv = pd.to_datetime(df[rule_f], errors="coerce", utc=True, format="mixed").astype("int64").to_numpy(dtype=float)
    rv[pd.to_datetime(df[rule_f], errors="coerce", utc=True, format="mixed").isna().to_numpy()] = np.nan
elif rule in ("HIGHEST", "LOWEST"):
    rv = pd.to_numeric(df[rule_f], errors="coerce").to_numpy(dtype=float)
else:
    rv = np.zeros(n)
sign = -1 if rule in ("LATEST", "HIGHEST") else 1
order = pd.DataFrame({"g": gid, "r": np.nan_to_num(sign * rv, nan=np.inf), "c": -completeness, "i": np.arange(n)})
order = order.sort_values(["g", "r", "c", "i"] if rule != "COMPLETE" else ["g", "c", "i"], kind="mergesort")
surv_idx = order.groupby("g")["i"].first().to_numpy() if n else np.array([], dtype=int)
is_surv = np.zeros(n, dtype=bool)
is_surv[surv_idx] = True

out = df.copy()
out["Duplicate Group"] = (gid + 1).astype("int64")
out["Group Size"] = gsize.astype("int64")
out["Survivor"] = np.where(is_surv, "Yes", "No")
out["Linked By"] = [lb if gsize[i] > 1 else None for i, lb in enumerate(linked_by)]
out["Filled Fields"] = completeness.astype("int64")

surv = df.iloc[surv_idx].copy()
filled_from = [[] for _ in range(len(surv_idx))]
if fill and n:
    for j, s in enumerate(surv_idx):
        members = np.nonzero(gid == gid[s])[0]
        if len(members) < 2:
            continue
        others = [m for m in order[order["g"] == gid[s]]["i"].tolist() if m != s]
        for c in df.columns:
            if not filled.iat[s, df.columns.get_loc(c)]:
                for m in others:
                    if filled.iat[m, df.columns.get_loc(c)]:
                        surv.iat[j, surv.columns.get_loc(c)] = df.iat[m, df.columns.get_loc(c)]
                        filled_from[j].append(c)
                        break
surv["Duplicate Group"] = (gid[surv_idx] + 1).astype("int64")
surv["Records Merged"] = gsize[surv_idx].astype("int64")
surv["Fields Filled From Duplicates"] = ["; ".join(x) if x else None for x in filled_from]
surv = surv.sort_values("Duplicate Group", kind="mergesort").reset_index(drop=True)
grp = pd.DataFrame({"Duplicate Group": np.arange(1, gid.max() + 2 if n else 1).astype("int64")})
if n:
    grp["Records"] = np.bincount(gid).astype("int64")
    grp["Survivor Row"] = (surv_idx[np.argsort(gid[surv_idx])] + 1).astype("int64")
    grp = grp[grp["Records"] > 1].reset_index(drop=True)
    grp["Linked By"] = [", ".join(sorted({linked_by[i] for i in np.nonzero(gid == g - 1)[0] if linked_by[i]})) for g in grp["Duplicate Group"]]
omniscope_api.write_output(out, "records")
omniscope_api.write_output(surv, "survivors")
omniscope_api.write_output(grp, "groups")
dups = int((gsize > 1).sum())
omniscope_api.close(f"{n:,} records: {len(grp):,} duplicate groups covering {dups:,} records; {len(surv):,} records after de-duplication"
                    + (f" (gaps filled from duplicates in {sum(1 for x in filled_from if x):,})" if fill else "") + ".")
