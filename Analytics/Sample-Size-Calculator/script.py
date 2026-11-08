"""Sample Size Calculator: how many observations an A/B test or survey needs.

  PROPORTION  two groups, conversion or response rates: baseline rate and the
              smallest lift worth detecting (relative, such as 10%, or absolute)
  MEAN        two groups, averages: standard deviation and the smallest difference
  SURVEY      one sample, estimating a proportion to a margin of error, with an
              optional finite population (fewer needed from a small population)

Each row of the optional input is a scenario; columns are matched by name,
ignoring case and spaces (Scenario, Type, Baseline, Effect, Relative Effect,
SD, Margin, Population, Alpha, Power, Sides, Ratio, Daily Traffic). Values the
input does not give come from the options, so without an input the options
describe a single scenario.

Outputs: the sample size per group and in total, the days needed at the given
traffic, the effect in both relative and absolute terms; and a power curve
(power against sample size) for each two-group scenario.
"""
import math
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


DEF = {"type": opt("test_type", "PROPORTION"), "baseline": float(opt("baseline", 0.05)), "effect": float(opt("effect", 0.10)),
       "relative": bool(opt("relative_effect", True)), "sd": float(opt("sd", 1.0) or 1.0), "margin": float(opt("margin", 0.03)),
       "population": float(opt("population", 0) or 0), "alpha": float(opt("alpha", 0.05)), "power": float(opt("power", 0.8)),
       "sides": int(opt("sides", 2)), "ratio": float(opt("ratio", 1.0) or 1.0), "traffic": float(opt("daily_traffic", 0) or 0)}

df = omniscope_api.read_input_records(input_number=0)


def norm_cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2))


def norm_ppf(p):
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - 0.02425:
        return -norm_ppf(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


ALIASES = {"scenario": "scenario", "name": "scenario", "type": "type", "testtype": "type", "baseline": "baseline", "baselinerate": "baseline",
           "effect": "effect", "mde": "effect", "minimumdetectableeffect": "effect", "relativeeffect": "relative", "relative": "relative",
           "sd": "sd", "standarddeviation": "sd", "margin": "margin", "marginoferror": "margin", "population": "population",
           "alpha": "alpha", "significance": "alpha", "power": "power", "sides": "sides", "ratio": "ratio", "allocationratio": "ratio",
           "dailytraffic": "traffic", "traffic": "traffic"}


def truth(v):
    return str(v).strip().lower() in ("1", "1.0", "true", "yes", "y", "relative")


scen = []
if df is not None and len(df):
    cmap = {}
    for c in df.columns:
        k = ALIASES.get(re.sub(r"[^a-z]", "", str(c).lower()))
        if k and k not in cmap:
            cmap[k] = c
    for i, r in df.reset_index(drop=True).iterrows():
        s = dict(DEF)
        s["scenario"] = str(r[cmap["scenario"]]) if "scenario" in cmap and pd.notna(r[cmap["scenario"]]) else f"Scenario {i + 1}"
        for k, c in cmap.items():
            v = r[c]
            if k == "scenario" or v is None or pd.isna(v) or str(v).strip() == "":
                continue
            if k == "type":
                s["type"] = str(v).strip().upper()
            elif k == "relative":
                s["relative"] = truth(v)
            else:
                try:
                    s[k] = float(str(v).strip().rstrip("%")) / (100.0 if str(v).strip().endswith("%") else 1.0)
                except ValueError:
                    omniscope_api.abort(f"Scenario '{s['scenario']}': '{v}' in column '{c}' is not a number.")
        scen.append(s)
else:
    scen.append({**DEF, "scenario": "Scenario 1"})


def n_for(s):
    """Returns (n group 1, n group 2, absolute effect, relative effect, rate 2) or raises ValueError."""
    za = norm_ppf(1 - s["alpha"] / s["sides"])
    zb = norm_ppf(s["power"])
    if s["type"] == "PROPORTION":
        p1 = s["baseline"]
        d = s["effect"] * p1 if s["relative"] else s["effect"]
        p2 = p1 + d
        if not (0 < p1 < 1 and 0 < p2 < 1) or d == 0:
            raise ValueError(f"rates must stay between 0 and 1 and differ (baseline {p1:g}, target {p2:g})")
        k = s["ratio"]
        pbar = (p1 + k * p2) / (1 + k)
        n1 = (za * math.sqrt(pbar * (1 - pbar) * (1 + 1 / k)) + zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2) / k)) ** 2 / d ** 2
        return n1, k * n1, d, d / p1, p2
    if s["type"] == "MEAN":
        d = s["effect"] * s["baseline"] if s["relative"] else s["effect"]
        if d == 0 or s["sd"] <= 0:
            raise ValueError("the difference must be non-zero and the standard deviation positive")
        k = s["ratio"]
        n1 = (1 + 1 / k) * (za + zb) ** 2 * s["sd"] ** 2 / d ** 2
        return n1, k * n1, d, d / s["baseline"] if s["baseline"] else np.nan, s["baseline"] + d
    if s["type"] == "SURVEY":
        p = s["baseline"] if 0 < s["baseline"] < 1 else 0.5
        z = norm_ppf(1 - s["alpha"] / 2)
        n0 = z ** 2 * p * (1 - p) / s["margin"] ** 2
        n = n0 / (1 + (n0 - 1) / s["population"]) if s["population"] > 0 else n0
        return n, 0.0, s["margin"], np.nan, np.nan
    raise ValueError(f"unknown type '{s['type']}' (use PROPORTION, MEAN or SURVEY)")


def power_at(s, n1):
    za = norm_ppf(1 - s["alpha"] / s["sides"])
    k = s["ratio"]
    if s["type"] == "PROPORTION":
        p1 = s["baseline"]
        d = s["effect"] * p1 if s["relative"] else s["effect"]
        p2 = p1 + d
        pbar = (p1 + k * p2) / (1 + k)
        se0 = math.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / (k * n1)))
        se1 = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / (k * n1))
        return norm_cdf((abs(d) - za * se0) / se1)
    d = s["effect"] * s["baseline"] if s["relative"] else s["effect"]
    se = s["sd"] * math.sqrt(1 / n1 + 1 / (k * n1))
    return norm_cdf(abs(d) / se - za)


rows, curve = [], []
for s in scen:
    for k_, lo, hi in (("alpha", 0, 0.5), ("power", 0.5, 0.9999)):
        if not lo < s[k_] < hi:
            omniscope_api.abort(f"Scenario '{s['scenario']}': {k_} must be between {lo} and {hi} (got {s[k_]:g}).")
    s["sides"] = int(s["sides"]) if s["sides"] in (1, 2) else s["sides"]
    if s["sides"] not in (1, 2):
        omniscope_api.abort(f"Scenario '{s['scenario']}': sides must be 1 or 2.")
    try:
        n1, n2, d_abs, d_rel, target = n_for(s)
    except ValueError as e:
        omniscope_api.abort(f"Scenario '{s['scenario']}': {e}")
    n1c, n2c = math.ceil(n1 - 1e-9), math.ceil(n2 - 1e-9)
    total = n1c + n2c
    rows.append({"Scenario": s["scenario"], "Type": s["type"], "Baseline": s["baseline"], "Target": target, "Absolute Effect": d_abs, "Relative Effect": d_rel,
                 "Standard Deviation": s["sd"] if s["type"] == "MEAN" else np.nan, "Margin Of Error": s["margin"] if s["type"] == "SURVEY" else np.nan,
                 "Population": s["population"] if s["type"] == "SURVEY" and s["population"] > 0 else np.nan, "Alpha": s["alpha"],
                 "Power": s["power"] if s["type"] != "SURVEY" else np.nan, "Sides": s["sides"] if s["type"] != "SURVEY" else 2,
                 "Allocation Ratio": s["ratio"] if s["type"] != "SURVEY" else np.nan, "Sample Size Group 1": n1c,
                 "Sample Size Group 2": n2c if s["type"] != "SURVEY" else None, "Total Sample Size": total,
                 "Daily Traffic": s["traffic"] if s["traffic"] > 0 else np.nan, "Days Needed": math.ceil(total / s["traffic"]) if s["traffic"] > 0 else None})
    if s["type"] != "SURVEY":
        for f in np.linspace(0.1, 2.0, 39):
            nn = max(2, int(round(n1c * f)))
            curve.append({"Scenario": s["scenario"], "Sample Size Group 1": nn, "Total Sample Size": int(round(nn * (1 + s["ratio"]))), "Power": power_at(s, nn),
                          "Share Of Required": float(f)})
res = pd.DataFrame(rows)
for c in ("Sample Size Group 1", "Total Sample Size", "Sides"):
    res[c] = res[c].astype("int64")
for c in ("Sample Size Group 2", "Days Needed"):
    res[c] = pd.array(pd.to_numeric(res[c]).to_numpy(dtype=float), dtype="Float64").astype("Int64")
for c in ("Baseline", "Target", "Absolute Effect", "Relative Effect", "Standard Deviation", "Margin Of Error", "Population", "Alpha", "Power", "Allocation Ratio", "Daily Traffic"):
    res[c] = res[c].astype("float64")
cv = pd.DataFrame(curve, columns=["Scenario", "Sample Size Group 1", "Total Sample Size", "Power", "Share Of Required"])
for c in ("Sample Size Group 1", "Total Sample Size"):
    cv[c] = cv[c].astype("int64")
for c in ("Power", "Share Of Required"):
    cv[c] = cv[c].astype("float64")
omniscope_api.write_output(res, "sizes")
omniscope_api.write_output(cv, "power_curve")
omniscope_api.close(f"{len(res)} scenario(s); total sample sizes from {res['Total Sample Size'].min():,} to {res['Total Sample Size'].max():,}.")
