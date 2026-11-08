"""Churn Survival Curves: Kaplan-Meier retention curves from start and end
dates (customers, subscriptions, contracts, employees, machines), with
customers still active counted correctly as censored rather than dropped.

  Survival (retention) at each time with a confidence band (Greenwood
  variance, log-log transform), the number at risk, ended and censored;
  median lifetime with its confidence interval; retention at milestones you
  choose (for example 3, 6, 12, 24 months); restricted mean lifetime up to a
  common horizon; and log-rank tests: all groups together, and each group
  against the rest.
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


start_f = opt("start_field")
end_f = opt("end_field")
dur_f = opt("duration_field")
event_f = opt("event_field")
group_f = opt("group_field")
unit = opt("unit", "MONTH")
as_of_txt = opt("as_of", "")
conf = float(opt("confidence", 0.95))
milestones_txt = opt("milestones", "3, 6, 12, 24")
UNIT_DAYS = {"DAY": 1.0, "WEEK": 7.0, "MONTH": 365.25 / 12, "YEAR": 365.25}

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the customers (one row each) to the input.")
if not dur_f and not start_f:
    omniscope_api.abort("Choose a start date field (with an end date field), or a duration field.")
for f in (start_f, end_f, dur_f, event_f, group_f):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")
if not 0.5 <= conf < 1:
    omniscope_api.abort("Confidence level must be between 0.5 and 0.999.")
try:
    milestones = sorted({float(x) for x in re.split(r"[,;\s]+", milestones_txt or "") if x.strip()})
except ValueError:
    omniscope_api.abort("Milestones must be numbers, for example: 3, 6, 12, 24")


def norm_ppf(p):
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p > 1 - 0.02425:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def gammaincc(a, x):
    """Regularised upper incomplete gamma Q(a, x) (Numerical Recipes)."""
    if x <= 0:
        return 1.0
    gln = math.lgamma(a)
    if x < a + 1:
        ap, s = a, 1.0 / a
        d = s
        for _ in range(1000):
            ap += 1
            d *= x / ap
            s += d
            if abs(d) < abs(s) * 1e-15:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - gln)
    b = x + 1 - a
    c, d = 1e300, 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = b + an / c
        c = c if abs(c) > 1e-300 else 1e-300
        de = d * c
        h *= de
        if abs(de - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def chi2_sf(x, k):
    return gammaincc(k / 2.0, x / 2.0) if x > 0 else 1.0


def to_date(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s
    else:
        txt = s.astype(object).where(s.notna(), None).astype(str).str.strip()
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        d = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        d[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
        d[~iso & s.notna()] = pd.to_datetime(txt[~iso & s.notna()], errors="coerce", dayfirst=True, format="mixed")
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    return d.astype("datetime64[ns]")


def truthy(s):
    if pd.api.types.is_bool_dtype(s):
        return s.fillna(False).to_numpy(dtype=bool)
    num = pd.to_numeric(s, errors="coerce")
    txt = s.astype(object).where(s.notna(), "").map(lambda v: str(v).strip().lower())
    return (num.fillna(0).to_numpy() != 0) | txt.isin(["yes", "y", "true", "churned", "ended", "cancelled", "canceled", "lapsed", "left", "event"]).to_numpy()


Z = norm_ppf(1 - (1 - conf) / 2)
if dur_f:
    T = pd.to_numeric(df[dur_f], errors="coerce").astype("float64").to_numpy()
    E = truthy(df[event_f]) if event_f else np.ones(len(df), dtype=bool)
else:
    st = to_date(df[start_f])
    en = to_date(df[end_f]) if end_f else pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    if as_of_txt:
        as_of = to_date(pd.Series([as_of_txt], dtype=object)).iloc[0]
        if pd.isna(as_of):
            omniscope_api.abort("The 'as of' date must be a date, such as 2025-12-31.")
    else:
        as_of = max(st.max(), en.max()) if (st.notna().any() or en.notna().any()) else pd.NaT
    ended = en.notna() & (en <= as_of)
    stop = en.where(ended, as_of)
    T = ((stop - st).dt.days / UNIT_DAYS[unit]).to_numpy(dtype=float)
    E = ended.to_numpy()
    if event_f:
        E = E & truthy(df[event_f])
G = df[group_f].astype(object).where(df[group_f].notna(), "(blank)").map(str).to_numpy() if group_f else np.array(["All"] * len(df), dtype=object)
ok = ~np.isnan(T) & (T >= 0)
skipped = int((~ok).sum())
T, E, G = T[ok], E[ok], G[ok]


def km(t, e):
    """Kaplan-Meier table at each distinct time with an event or censoring."""
    if len(t) == 0:
        return pd.DataFrame(columns=["Time", "At Risk", "Ended", "Censored", "Survival", "CI Low", "CI High"])
    order = np.argsort(t, kind="mergesort")
    t, e = t[order], e[order]
    ut, idx = np.unique(t, return_inverse=True)
    d = np.bincount(idx, weights=e.astype(float))
    c = np.bincount(idx, weights=(~e).astype(float))
    n_at = len(t) - np.concatenate([[0], np.cumsum(d + c)[:-1]])
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.cumprod(np.where(n_at > 0, 1 - d / n_at, 1.0))
        gw = np.cumsum(np.where((n_at > d) & (n_at > 0), d / (n_at * (n_at - d)), 0.0))
        # log-log (complementary log-log) interval, as in most statistics packages
        lls = np.log(-np.log(s))
        se = np.sqrt(gw) / np.abs(np.log(s))
        lo = np.exp(-np.exp(lls + Z * se))
        hi = np.exp(-np.exp(lls - Z * se))
    lo = np.where(s >= 1, 1.0, np.where(s <= 0, 0.0, lo))
    hi = np.where(s >= 1, 1.0, np.where(s <= 0, 0.0, hi))
    return pd.DataFrame({"Time": ut, "At Risk": n_at.astype(int), "Ended": d.astype(int), "Censored": c.astype(int), "Survival": s,
                         "CI Low": np.nan_to_num(lo, nan=0.0), "CI High": np.nan_to_num(hi, nan=1.0)})


def surv_at(tab, x, col="Survival"):
    if tab.empty:
        return np.nan
    k = np.searchsorted(tab["Time"].to_numpy(), x, side="right") - 1
    return 1.0 if k < 0 else float(tab[col].iloc[k])


def median_of(tab, col="Survival"):
    s = tab[col].to_numpy()
    k = np.nonzero(s <= 0.5)[0]
    return float(tab["Time"].iloc[k[0]]) if len(k) else np.nan


def rmst(tab, horizon):
    if tab.empty or not horizon == horizon:
        return np.nan
    t = np.concatenate([[0.0], tab["Time"].to_numpy()])
    s = np.concatenate([[1.0], tab["Survival"].to_numpy()])
    keep = t < horizon
    t, s = t[keep], s[keep]
    widths = np.diff(np.concatenate([t, [horizon]]))
    return float((s * widths).sum())


def logrank(t, e, g):
    """k-sample log-rank test; returns chi-square, df, p, and observed / expected events per group."""
    groups = sorted(set(g))
    if len(groups) < 2:
        return np.nan, 0, np.nan, {}
    ut = np.unique(t[e])
    k = len(groups)
    O = np.zeros(k)
    Ex = np.zeros(k)
    V = np.zeros((k, k))
    gi = np.array([groups.index(x) for x in g])
    for tt in ut:
        at = t >= tt
        n_j = np.array([(at & (gi == j)).sum() for j in range(k)], dtype=float)
        d_j = np.array([((t == tt) & e & (gi == j)).sum() for j in range(k)], dtype=float)
        n, d = n_j.sum(), d_j.sum()
        if n <= 1:
            continue
        O += d_j
        Ex += d * n_j / n
        f = d * (n - d) / (n - 1) / n
        V += f * (np.diag(n_j) - np.outer(n_j, n_j) / n)
    diff = (O - Ex)[:-1]
    Vr = V[:-1, :-1]
    try:
        chi = float(diff @ np.linalg.solve(Vr, diff))
    except np.linalg.LinAlgError:
        chi = float(diff @ np.linalg.pinv(Vr) @ diff)
    return chi, k - 1, chi2_sf(chi, k - 1), {groups[j]: (O[j], Ex[j]) for j in range(k)}


groups = sorted(set(G)) if group_f else ["All"]
tabs = {g: km(T[G == g], E[G == g]) for g in groups}
horizon = min((float(T[G == g].max()) for g in groups if (G == g).any()), default=np.nan)

curve_parts = []
for g in groups:
    tb = tabs[g].copy()
    start_row = pd.DataFrame({"Time": [0.0], "At Risk": [int((G == g).sum())], "Ended": [0], "Censored": [0], "Survival": [1.0], "CI Low": [1.0], "CI High": [1.0]})
    rest = tb[tb["Time"] > 0]
    # concatenate only non-empty frames (pandas 2.x warns about empty ones; same result in pandas 3)
    tb = tb.reset_index(drop=True) if (tb["Time"] == 0).any() else (pd.concat([start_row, rest], ignore_index=True) if len(rest) else start_row)
    tb.insert(0, "Group", g)
    curve_parts.append(tb)
curve = pd.concat(curve_parts, ignore_index=True) if curve_parts else pd.DataFrame()
if len(curve):
    for c in ("At Risk", "Ended", "Censored"):
        curve[c] = curve[c].astype("int64")
    curve["Ended So Far"] = curve.groupby("Group")["Ended"].cumsum().astype("int64")
    for c in ("Time", "Survival", "CI Low", "CI High"):
        curve[c] = curve[c].astype("float64")
    curve["Churned Share"] = (1 - curve["Survival"]).astype("float64")
if not group_f and len(curve):
    curve = curve.drop(columns=["Group"])

chi_all, dfree, p_all, oe = logrank(T, E, G) if group_f else (np.nan, 0, np.nan, {})
srows = []
for g in groups:
    tb = tabs[g]
    m = G == g
    rec = {"Group": g, "Customers": int(m.sum()), "Ended": int(E[m].sum()), "Still Active (censored)": int((~E[m]).sum()),
           "Median Lifetime": median_of(tb) if len(tb) else np.nan,
           "Median CI Low": median_of(tb, "CI Low") if len(tb) else np.nan, "Median CI High": median_of(tb, "CI High") if len(tb) else np.nan}
    for ms in milestones:
        lab = f"{ms:g}"
        rec[f"Retention At {lab}"] = surv_at(tb, ms) if ms <= (T[m].max() if m.any() else -1) else np.nan
    rec["Restricted Mean Lifetime"] = rmst(tb, horizon)
    if group_f:
        o, ex = oe.get(g, (np.nan, np.nan))
        rec["Observed Ended"], rec["Expected Ended"] = o, ex
        c2, _, p2, _ = logrank(T, E, np.where(G == g, "g", "rest"))
        rec["Log-Rank Chi-Square Vs Rest"], rec["P Value Vs Rest"] = c2, p2
        rec["Vs Rest"] = ("Not tested" if p2 != p2 else ("Shorter lifetimes" if o > ex else "Longer lifetimes") if p2 < 1 - conf else "Not significant")
    srows.append(rec)
summ = pd.DataFrame(srows)
if not group_f:
    summ = summ.drop(columns=["Group"])
for c in summ.columns:
    if c in ("Customers", "Ended", "Still Active (censored)"):
        summ[c] = summ[c].astype("int64")
    elif c not in ("Group", "Vs Rest"):
        summ[c] = summ[c].astype("float64")
tests = pd.DataFrame([{"Test": "Log-rank, all groups", "Groups": len(groups), "Chi-Square": chi_all, "Degrees Of Freedom": dfree, "P Value": p_all,
                       "Significant": ("Yes" if p_all < 1 - conf else "No") if p_all == p_all else "Not tested",
                       "Restricted Mean Horizon": horizon}])
tests["Groups"] = tests["Groups"].astype("int64")
tests["Degrees Of Freedom"] = tests["Degrees Of Freedom"].astype("int64")
for c in ("Chi-Square", "P Value", "Restricted Mean Horizon"):
    tests[c] = tests[c].astype("float64")

omniscope_api.write_output(curve, "curve")
omniscope_api.write_output(summ, "summary")
omniscope_api.write_output(tests, "tests")
tot_med = median_of(km(T, E)) if len(T) else np.nan
omniscope_api.close(f"{len(T):,} customers, {int(E.sum()):,} ended, {int((~E).sum()):,} still active; median lifetime "
                    + (f"{tot_med:.1f} {unit.lower()}s" if tot_med == tot_med else "not reached")
                    + (f"; log-rank p = {p_all:.3g} across {len(groups)} groups" if group_f and p_all == p_all else "")
                    + (f"; {skipped:,} rows without a valid start or duration skipped" if skipped else "") + ".")
