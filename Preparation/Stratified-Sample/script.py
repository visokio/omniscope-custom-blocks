"""Stratified Sample: draw a random sample within strata (groups) so every
group is represented: a fixed number or percentage per stratum, or a total
sample allocated proportionally (with a minimum per stratum) or equally.
Reproducible with a seed. Outputs the sample (with sampling weights), the
records not sampled, and the allocation per stratum.
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


strata = opt("strata_fields", []) or []
method = opt("method", "PROPORTIONAL")
total_n = int(opt("total_n", 100))
per_n = int(opt("per_stratum_n", 10))
percent = float(opt("percent", 10.0))
min_per = int(opt("min_per_stratum", 1))
seed = int(opt("seed", 42))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the population to sample from to the input.")
miss = [s for s in strata if s not in df.columns]
if miss:
    omniscope_api.abort(f"Strata fields not in the input: {', '.join(miss)}")
if method in ("PROPORTIONAL", "EQUAL") and total_n < 0:
    omniscope_api.abort("Total sample size must be 0 or more.")
if method == "PERCENT" and not 0 <= percent <= 100:
    omniscope_api.abort("Percentage must be between 0 and 100.")

if strata:
    keys = [df[c].astype(object).where(df[c].notna(), "(blank)") for c in strata]
    groups = {k if isinstance(k, tuple) else (k,): v for k, v in pd.Series(np.arange(len(df))).groupby(keys, sort=True).indices.items()}
else:
    groups = {(): np.arange(len(df))}

sizes = {k: len(v) for k, v in groups.items()}
N = sum(sizes.values())
alloc = {}
if method == "FIXED":
    alloc = {k: min(per_n, n) for k, n in sizes.items()}
elif method == "PERCENT":
    alloc = {k: min(n, int(math.floor(n * percent / 100 + 0.5))) for k, n in sizes.items()}
elif method == "EQUAL":
    target = min(total_n, N)
    alloc = {k: 0 for k in sizes}
    remaining = target
    open_ = [k for k in sizes if sizes[k] > 0]
    while remaining > 0 and open_:
        share = max(1, remaining // len(open_))
        for k in list(open_):
            take = min(share, sizes[k] - alloc[k], remaining)
            alloc[k] += take
            remaining -= take
            if alloc[k] >= sizes[k]:
                open_.remove(k)
            if remaining == 0:
                break
elif method == "PROPORTIONAL":
    target = min(total_n, N)
    floor_ = {k: min(sizes[k], min_per) for k in sizes}
    if sum(floor_.values()) > target:
        omniscope_api.abort(f"The minimum of {min_per} per stratum needs {sum(floor_.values())} records, more than the total sample of {target}.")
    # strata whose proportional share falls below the minimum (or above capacity) are fixed there;
    # the rest of the sample is shared proportionally among the others; repeat until stable
    fixed = {}
    while True:
        free = [k for k in sizes if k not in fixed]
        rest = target - sum(fixed.values())
        tot = sum(sizes[k] for k in free)
        ideal = {k: rest * sizes[k] / tot if tot else 0 for k in free}
        changed = False
        for k in free:
            if ideal[k] < floor_[k]:
                fixed[k] = floor_[k]
                changed = True
            elif ideal[k] > sizes[k]:
                fixed[k] = sizes[k]
                changed = True
        if not changed:
            break
    alloc = dict(fixed)
    base = {k: int(math.floor(ideal[k])) for k in free}
    alloc.update(base)
    left = target - sum(alloc.values())
    for k in sorted(free, key=lambda k: (-(ideal[k] - math.floor(ideal[k])), str(k))):
        if left <= 0:
            break
        if alloc[k] < sizes[k]:
            alloc[k] += 1
            left -= 1
else:
    omniscope_api.abort(f"Unknown method {method}")

rng = np.random.default_rng(seed)
chosen = np.zeros(len(df), dtype=bool)
weight = np.full(len(df), np.nan)
for k, idx in groups.items():
    m = alloc.get(k, 0)
    if m > 0:
        pick = rng.choice(idx, size=m, replace=False)
        chosen[pick] = True
        weight[pick] = sizes[k] / m

sample = df[chosen].copy()
sample["Sample Weight"] = weight[chosen]
if strata:
    sample["Stratum"] = pd.Series([" | ".join(str(v) for v in row) for row in sample[strata].astype(object).where(sample[strata].notna(), "(blank)").to_numpy()],
                                  index=sample.index, dtype=object)
else:
    sample["Stratum"] = pd.Series(["All"] * len(sample), index=sample.index, dtype=object)
remainder = df[~chosen].copy()
rows = []
for k in sorted(groups, key=lambda x: tuple(str(v) for v in x)):
    n, m = sizes[k], alloc.get(k, 0)
    rows.append({**{c: k[i] for i, c in enumerate(strata)}, "Population": n, "Sample Size": m,
                 "Sampling Fraction": m / n if n else np.nan, "Sample Weight": n / m if m else np.nan,
                 "Share Of Population": n / N if N else np.nan, "Share Of Sample": m / max(1, sum(alloc.values()))})
summ = pd.DataFrame(rows, columns=list(strata) + ["Population", "Sample Size", "Sampling Fraction", "Sample Weight", "Share Of Population", "Share Of Sample"])
summ["Population"] = summ["Population"].astype("int64")
summ["Sample Size"] = summ["Sample Size"].astype("int64")
for c in ("Sampling Fraction", "Sample Weight", "Share Of Population", "Share Of Sample"):
    summ[c] = summ[c].astype("float64")

omniscope_api.write_output(sample, "sample")
omniscope_api.write_output(remainder, "remainder")
omniscope_api.write_output(summ, "allocation")
omniscope_api.close(f"{int(chosen.sum()):,} of {N:,} records sampled from {len(groups):,} strata ({method.lower()}, seed {seed}).")
