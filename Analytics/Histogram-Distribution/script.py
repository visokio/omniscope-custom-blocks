"""Histogram and Distribution: bin a numeric field into a histogram, overall or
per group, with the bin width chosen automatically (Freedman-Diaconis, using
the interquartile range, or Sturges) or set by you, shared across groups so
their histograms line up, plus the summary statistics analysts look at next:
count, missing, mean, standard deviation, minimum, quartiles, percentiles,
maximum, skewness and kurtosis.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


val_f = opt("value_field")
group_f = opt("group_field")
rule = opt("bin_rule", "FD")
width_opt = float(opt("bin_width", 0) or 0)
n_bins_opt = int(opt("bins", 0) or 0)
clip = float(opt("clip_percentile", 0) or 0)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
if not val_f or val_f not in df.columns:
    omniscope_api.abort(f"Choose the value field (got '{val_f}').")
if group_f and group_f not in df.columns:
    omniscope_api.abort(f"Field '{group_f}' is not in the input.")
x = pd.to_numeric(df[val_f], errors="coerce").astype("float64")
if df[val_f].notna().any() and x.isna().all():
    omniscope_api.abort(f"The value field '{val_f}' must be numeric.")
g = df[group_f].astype(object).where(df[group_f].notna(), "(blank)").map(str) if group_f else pd.Series("All", index=df.index)
v = x.dropna()
if v.empty:
    lo = hi = 0.0
else:
    lo, hi = (np.percentile(v, [clip, 100 - clip]) if 0 < clip < 50 else (v.min(), v.max()))
span = hi - lo
n = len(v)
if width_opt > 0:
    width = width_opt
elif n_bins_opt > 0:
    width = span / n_bins_opt if span > 0 else 1.0
elif rule == "STURGES":
    width = span / max(1, int(np.ceil(np.log2(max(n, 1)) + 1))) if span > 0 else 1.0
else:
    iqr = np.subtract(*np.percentile(v, [75, 25])) if n else 0.0
    width = 2 * iqr / n ** (1 / 3) if iqr > 0 and n else (span / 10 if span > 0 else 1.0)
nb = int(np.ceil(span / width)) if span > 0 else 1
if nb > 2000:
    nb, width = 2000, span / 2000
start = np.floor(lo / width) * width if span > 0 else lo
edges = start + width * np.arange(nb + 2)
edges = edges[: np.searchsorted(edges, hi, side="right") + 1]
if len(edges) < 2:
    edges = np.array([lo, lo + width])
hrows, srows = [], []
parts = [(gname, x[g == gname]) for gname in sorted(g.unique())] + ([("All", x)] if group_f else [])
for gname, xs in parts:
    vals = xs.dropna().to_numpy()
    inside = vals[(vals >= edges[0]) & (vals <= edges[-1])]
    cnt, _ = np.histogram(inside, edges)
    below, above = int((vals < edges[0]).sum()), int((vals > edges[-1]).sum())
    for b in range(len(cnt)):
        hrows.append({"Group": gname, "Bin": b + 1, "From": float(edges[b]), "To": float(edges[b + 1]), "Midpoint": float((edges[b] + edges[b + 1]) / 2),
                      "Count": int(cnt[b]), "Share": cnt[b] / len(vals) if len(vals) else np.nan,
                      "Cumulative Share": (cnt[: b + 1].sum() + below) / len(vals) if len(vals) else np.nan})
    q = np.percentile(vals, [1, 5, 25, 50, 75, 95, 99]) if len(vals) else [np.nan] * 7
    m, sd = (vals.mean(), vals.std(ddof=1)) if len(vals) > 1 else ((vals.mean() if len(vals) else np.nan), np.nan)
    z = (vals - m) / vals.std(ddof=0) if len(vals) > 2 and vals.std(ddof=0) > 0 else None
    srows.append({"Group": gname, "Count": int(len(vals)), "Missing": int(xs.isna().sum()), "Mean": m, "Std Dev": sd, "Minimum": vals.min() if len(vals) else np.nan,
                  "P1": q[0], "P5": q[1], "Q1": q[2], "Median": q[3], "Q3": q[4], "P95": q[5], "P99": q[6], "Maximum": vals.max() if len(vals) else np.nan,
                  "Skewness": float((z ** 3).mean()) if z is not None else np.nan, "Excess Kurtosis": float((z ** 4).mean() - 3) if z is not None else np.nan,
                  "Below Range": below, "Above Range": above})
hist = pd.DataFrame(hrows)
summ = pd.DataFrame(srows)
for c in ("Bin", "Count"):
    hist[c] = hist[c].astype("int64")
for c in ("From", "To", "Midpoint", "Share", "Cumulative Share"):
    hist[c] = hist[c].astype("float64")
for c in summ.columns:
    if c in ("Count", "Missing", "Below Range", "Above Range"):
        summ[c] = summ[c].astype("int64")
    elif c != "Group":
        summ[c] = summ[c].astype("float64")
if group_f:
    hist = hist.rename(columns={"Group": str(group_f)})
    summ = summ.rename(columns={"Group": str(group_f)})
else:
    hist = hist.drop(columns=["Group"])
    summ = summ.drop(columns=["Group"])
omniscope_api.write_output(hist, "histogram")
omniscope_api.write_output(summ, "summary")
omniscope_api.close(f"{n:,} values in {len(edges) - 1} bins of width {width:,.4g} ({'set' if width_opt or n_bins_opt else rule}), {g.nunique() if group_f else 1} group(s).")
