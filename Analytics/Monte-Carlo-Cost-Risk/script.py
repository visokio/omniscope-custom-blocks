"""Monte Carlo Cost Risk: turn three-point estimates (low, most likely, high)
for each line of a budget, project estimate, bid or forecast into a
probability distribution of the total.

  Each line is sampled from a PERT (default), triangular or uniform
  distribution; optional risk events occur with a given probability; lines can
  be correlated (one rank correlation for all lines, applied with the
  Iman-Conover rank reordering), because independent lines understate the risk.

Outputs: P10 / P50 / P80 / P90 / P95 of the total (and per group), the
contingency needed above the base estimate for each confidence level, the
probability of exceeding the base or a target, which lines drive the
uncertainty (rank correlation with the total and share of variance), and the
S-curve of the total. A fixed random seed makes runs repeatable.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


name_f = opt("name_field")
low_f, ml_f, high_f = opt("low_field"), opt("likely_field"), opt("high_field")
prob_f = opt("probability_field")
group_f = opt("group_field")
dist = opt("distribution", "PERT")
iters = int(opt("iterations", 10000))
rho = float(opt("correlation", 0.0) or 0.0)
seed = int(opt("seed", 1))
target = opt("target")
target = float(target) if target not in (None, "") else None
bins = int(opt("bins", 50))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the estimate lines to the input.")
for f, lab in ((name_f, "line name"), (low_f, "low estimate"), (ml_f, "most likely estimate"), (high_f, "high estimate")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
for f in (prob_f, group_f):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")
if not 100 <= iters <= 1_000_000:
    omniscope_api.abort("Iterations must be between 100 and 1,000,000.")
if not 0 <= rho < 1:
    omniscope_api.abort("Correlation must be from 0 up to (not including) 1.")

lo = pd.to_numeric(df[low_f], errors="coerce").astype("float64").to_numpy()
ml = pd.to_numeric(df[ml_f], errors="coerce").astype("float64").to_numpy()
hi = pd.to_numeric(df[high_f], errors="coerce").astype("float64").to_numpy()
ml = np.where(np.isnan(ml), (lo + hi) / 2, ml)
lo = np.where(np.isnan(lo), ml, lo)
hi = np.where(np.isnan(hi), ml, hi)
bad = np.isnan(ml)
if bad.any():
    omniscope_api.abort(f"{int(bad.sum())} line(s) have no usable estimate (first: '{df[name_f].iloc[int(np.argmax(bad))]}').")
wrong = (lo > ml + 1e-12) | (ml > hi + 1e-12)
if wrong.any():
    i = int(np.argmax(wrong))
    omniscope_api.abort(f"Line '{df[name_f].iloc[i]}' needs low <= most likely <= high (got {lo[i]:g}, {ml[i]:g}, {hi[i]:g}).")
if prob_f:
    p = pd.to_numeric(df[prob_f], errors="coerce").astype("float64").to_numpy()
    p = np.where(p > 1, p / 100.0, p)  # percentages are accepted
    p = np.where(np.isnan(p), 1.0, p)
    if ((p < 0) | (p > 1)).any():
        omniscope_api.abort("Probabilities must be between 0 and 1 (or 0% and 100%).")
else:
    p = np.ones(len(df))
n = len(df)
if n * iters > 20_000_000:
    omniscope_api.abort(f"{n:,} lines x {iters:,} iterations is too many; use fewer iterations (at most {20_000_000 // max(n, 1):,}).")

rng = np.random.default_rng(seed)
span = hi - lo
S = np.empty((iters, n))
for j in range(n):
    if span[j] <= 0:
        S[:, j] = ml[j]
        continue
    if dist == "PERT":
        a = 1 + 4 * (ml[j] - lo[j]) / span[j]
        b = 1 + 4 * (hi[j] - ml[j]) / span[j]
        S[:, j] = lo[j] + span[j] * rng.beta(a, b, iters)
    elif dist == "TRIANGULAR":
        S[:, j] = rng.triangular(lo[j], ml[j], hi[j], iters) if hi[j] > lo[j] else ml[j]
    else:
        S[:, j] = rng.uniform(lo[j], hi[j], iters)
if rho > 0 and n > 1:
    # Iman-Conover: reorder each column so its ranks follow equicorrelated normal scores
    common = rng.standard_normal(iters)
    for j in range(n):
        zj = np.sqrt(rho) * common + np.sqrt(1 - rho) * rng.standard_normal(iters)
        order = np.argsort(np.argsort(zj))
        S[:, j] = np.sort(S[:, j])[order]
occurs = rng.random((iters, n)) < p
S = np.where(occurs, S, 0.0)
total = S.sum(axis=1)
certain = p >= 1
base = float(ml[certain].sum())                  # base estimate: most likely of the certain lines
risk_exp = float((ml * p)[~certain].sum())       # expected value of the risk events (probability x most likely)
PCTS = [10, 50, 80, 90, 95]


def stats(t, base_val, risk_val, label):
    q = np.percentile(t, PCTS)
    rec = {"Scope": label, "Base Estimate (most likely)": base_val, "Expected Risk Events": risk_val, "Mean": float(t.mean()), "Std Dev": float(t.std(ddof=1)),
           "Minimum": float(t.min()), "Maximum": float(t.max())}
    for k, v in zip(PCTS, q):
        rec[f"P{k}"] = float(v)
    rec["Probability Over Base"] = float((t > base_val).mean())
    for k in (50, 80, 90):
        rec[f"Contingency To P{k}"] = rec[f"P{k}"] - base_val
    if target is not None and label == "Total":
        rec["Target"] = target
        rec["Probability Over Target"] = float((t > target).mean())
        rec["Confidence Level Of Target"] = float((t <= target).mean())
    return rec


rows = [stats(total, base, risk_exp, "Total")]
if group_f:
    gv = df[group_f].astype(object).where(df[group_f].notna(), "(blank)").map(str).to_numpy()
    for g in sorted(set(gv)):
        m = gv == g
        rows.append(stats(S[:, m].sum(axis=1), float(ml[m & certain].sum()), float((ml * p)[m & ~certain].sum()), g))
summ = pd.DataFrame(rows)
for c in summ.columns:
    if c != "Scope":
        summ[c] = summ[c].astype("float64")
summ.insert(1, "Level", ["Total"] + ["Group"] * (len(summ) - 1))

# drivers: Spearman rank correlation of each line with the total, and share of variance
rt = np.argsort(np.argsort(total)).astype(float)
rt = (rt - rt.mean()) / (rt.std() or 1)
var_t = total.var()
drv = []
for j in range(n):
    col = S[:, j]
    if col.std() == 0:
        r = 0.0
    else:
        rc = np.argsort(np.argsort(col, kind="stable"), kind="stable").astype(float)
        rc = (rc - rc.mean()) / rc.std()
        r = float((rc * rt).mean())
    cov = float(np.cov(col, total)[0, 1]) if col.std() > 0 else 0.0
    q10, q90 = np.percentile(col, [10, 90])
    drv.append({"Line": df[name_f].iloc[j], **({"Group": gv[j]} if group_f else {}), "Low": lo[j], "Most Likely": ml[j], "High": hi[j],
                "Probability": p[j], "Mean": float(col.mean()), "Std Dev": float(col.std(ddof=1)), "P10": float(q10), "P90": float(q90),
                "Rank Correlation With Total": r, "Share Of Variance": cov / var_t if var_t > 0 else 0.0})
lines = pd.DataFrame(drv)
lines = lines.rename(columns={"Line": str(name_f)} | ({"Group": str(group_f)} if group_f else {}))
lines["Driver Rank"] = lines["Share Of Variance"].rank(ascending=False, method="first").astype("int64")
for c in ("Low", "Most Likely", "High", "Probability", "Mean", "Std Dev", "P10", "P90", "Rank Correlation With Total", "Share Of Variance"):
    lines[c] = lines[c].astype("float64")
lines = lines.sort_values("Driver Rank").reset_index(drop=True)

edges = np.linspace(total.min(), total.max(), bins + 1) if total.max() > total.min() else np.array([total.min(), total.min() + 1])
cnt, _ = np.histogram(total, edges)
curve = pd.DataFrame({"Bin": np.arange(1, len(cnt) + 1), "From": edges[:-1], "To": edges[1:], "Midpoint": (edges[:-1] + edges[1:]) / 2,
                      "Iterations": cnt.astype("int64"), "Probability": cnt / iters, "Cumulative Probability": np.cumsum(cnt) / iters})
curve["Bin"] = curve["Bin"].astype("int64")
for c in ("From", "To", "Midpoint", "Probability", "Cumulative Probability"):
    curve[c] = curve[c].astype("float64")

omniscope_api.write_output(summ, "summary")
omniscope_api.write_output(lines, "drivers")
omniscope_api.write_output(curve, "distribution")
t = summ.iloc[0]
omniscope_api.close(f"{iters:,} iterations of {n} lines ({dist.lower()}, correlation {rho:g}): base {base:,.0f}, P50 {t['P50']:,.0f}, P80 {t['P80']:,.0f}, P90 {t['P90']:,.0f}; "
                    f"{t['Probability Over Base']:.0%} chance of exceeding the base.")
