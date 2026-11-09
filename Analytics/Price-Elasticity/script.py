"""Price Elasticity: estimate the price elasticity of demand per product (or
segment) with a log-log regression of volume on price, optionally controlling
for other numeric drivers (promotion flag, distribution, seasonality dummies).

Elasticity b: a 1% price rise changes volume by about b%. |b| > 1 is elastic
(a price rise loses revenue), |b| < 1 inelastic (a price rise gains revenue).
Outputs: elasticity with confidence interval, p-value, R squared, observations,
interpretation and the estimated volume and revenue effect of a price change;
a fitted demand curve per product; and fitted values per observation.
Pure numpy (t-distribution computed here).
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


price_f = opt("price_field")
qty_f = opt("volume_field")
group_fields = opt("group_fields", []) or []
controls = opt("control_fields", []) or []
confidence = float(opt("confidence", 0.95))
change = float(opt("price_change_pct", 5.0))
min_obs = int(opt("min_observations", 12))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect price and volume observations to the input.")
for f, label in ((price_f, "price"), (qty_f, "volume")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
miss = [f for f in list(group_fields) + list(controls) if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")
if price_f in controls or qty_f in controls:
    omniscope_api.abort("Price and volume cannot also be control fields.")


def _betacf(a, b, x):
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = 1 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = 1 + aa / c if abs(1 + aa / c) > 1e-300 else 1e-300
        de = d * c
        h *= de
        if abs(de - 1) < 3e-14:
            break
    return h


def betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1 - math.exp(lbt) * _betacf(b, a, 1 - x) / b


def t_sf2(t, dfree):
    return betainc(dfree / 2, 0.5, dfree / (dfree + t * t)) if math.isfinite(t) else 0.0


def t_ppf(p, dfree):
    lo, hi = 0.0, 1000.0
    target = 2 * (1 - p)
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_sf2(mid, dfree) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


w = df.copy()
w["__p"] = pd.to_numeric(w[price_f], errors="coerce")
w["__q"] = pd.to_numeric(w[qty_f], errors="coerce")
for c in controls:
    w[c] = pd.to_numeric(w[c], errors="coerce")
usable = w["__p"].gt(0) & w["__q"].gt(0) & w[controls].notna().all(axis=1) if controls else w["__p"].gt(0) & w["__q"].gt(0)
dropped = int((~usable).sum())
w["__use"] = usable

groups = [((), w)] if not group_fields else [((k if isinstance(k, tuple) else (k,)), g) for k, g in w.groupby(group_fields, sort=True)]
res_rows, curve_rows = [], []
fitted = pd.Series(np.nan, index=w.index)
for key, g in groups:
    kd = {c: key[i] for i, c in enumerate(group_fields)}
    u = g[g["__use"]]
    n = len(u)
    k = 2 + len(controls)
    base = {**kd, "Observations": n}
    if n < max(min_obs, k + 2):
        res_rows.append({**base, "Status": f"Too few usable observations (need at least {max(min_obs, k + 2)})"})
        continue
    lp, lq = np.log(u["__p"].to_numpy(dtype=float)), np.log(u["__q"].to_numpy(dtype=float))
    if np.std(lp) < 1e-9:
        res_rows.append({**base, "Status": "Price never changes, so elasticity cannot be estimated"})
        continue
    X = np.column_stack([np.ones(n), lp] + [u[c].to_numpy(dtype=float) for c in controls])
    beta, *_ = np.linalg.lstsq(X, lq, rcond=None)
    resid = lq - X @ beta
    dfree = n - X.shape[1]
    sigma2 = float(resid @ resid) / dfree
    try:
        cov = sigma2 * np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        res_rows.append({**base, "Status": "Drivers are collinear; remove a control field"})
        continue
    b, se = float(beta[1]), float(math.sqrt(cov[1, 1]))
    tstat = b / se if se > 0 else float("inf")
    p = t_sf2(abs(tstat), dfree)
    crit = t_ppf(1 - (1 - confidence) / 2, dfree)
    ss_tot = float(((lq - lq.mean()) ** 2).sum())
    r2 = 1 - float(resid @ resid) / ss_tot if ss_tot > 0 else float("nan")
    fitted.loc[u.index] = np.exp(X @ beta)
    f = 1 + change / 100
    vol_eff = f ** b - 1
    rev_eff = f ** (b + 1) - 1
    if p >= 1 - confidence:
        reading = "No reliable price effect found in this data."
    elif b >= 0:
        reading = "Volume rises with price here: check for confounding (promotions, seasonality, supply limits)."
    elif b < -1:
        reading = f"Elastic: a {change:g}% price rise loses about {abs(vol_eff):.0%} of volume and {abs(rev_eff):.1%} of revenue."
    else:
        reading = f"Inelastic: a {change:g}% price rise loses about {abs(vol_eff):.0%} of volume but raises revenue by about {rev_eff:.1%}."
    res_rows.append({**base, "Status": "OK", "Elasticity": b, "CI Low": b - crit * se, "CI High": b + crit * se, "Standard Error": se,
                     "P Value": p, "R Squared": r2, "Average Price": float(u["__p"].mean()), "Min Price": float(u["__p"].min()),
                     "Max Price": float(u["__p"].max()), "Average Volume": float(u["__q"].mean()),
                     f"Volume Change For +{change:g}% Price": vol_eff, f"Revenue Change For +{change:g}% Price": rev_eff,
                     "Interpretation": reading})
    xbar = X[:, 2:].mean(axis=0) if controls else np.array([])
    for pr in np.linspace(u["__p"].min(), u["__p"].max(), 25):
        q = float(np.exp(beta[0] + b * math.log(pr) + (xbar @ beta[2:] if controls else 0.0)))
        curve_rows.append({**kd, "Price": float(pr), "Predicted Volume": q, "Predicted Revenue": float(pr * q)})

rcols = list(group_fields) + ["Observations", "Status", "Elasticity", "CI Low", "CI High", "Standard Error", "P Value", "R Squared",
                              "Average Price", "Min Price", "Max Price", "Average Volume", f"Volume Change For +{change:g}% Price",
                              f"Revenue Change For +{change:g}% Price", "Interpretation"]
rdf = pd.DataFrame(res_rows, columns=rcols)
rdf["Observations"] = rdf["Observations"].astype("int64")
for c in rcols[len(group_fields) + 2:-1]:
    rdf[c] = rdf[c].astype("float64")
cdf = pd.DataFrame(curve_rows, columns=list(group_fields) + ["Price", "Predicted Volume", "Predicted Revenue"])
for c in ("Price", "Predicted Volume", "Predicted Revenue"):
    cdf[c] = cdf[c].astype("float64")
obs = df.copy()
obs["Fitted Volume"] = fitted.astype("float64")
obs["Used In Model"] = np.where(usable, "Yes", "No")

omniscope_api.write_output(rdf, "elasticities")
omniscope_api.write_output(cdf, "curves")
omniscope_api.write_output(obs, "observations")
ok = rdf[rdf["Status"] == "OK"]
omniscope_api.close(f"{len(ok)} of {len(rdf)} elasticities estimated" + (f"; {dropped:,} rows unusable (zero / missing price or volume)." if dropped else "."))
