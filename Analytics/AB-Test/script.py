"""A/B Test: compare each variant with the control on a conversion rate
(two-proportion z-test) or a mean (Welch's t-test), with confidence interval,
relative lift, p-value, a plain-language verdict and the sample size needed to
confirm the observed effect. Optionally per segment, with Bonferroni correction.

Input either one row per visitor (variant + outcome) or one row per variant
(trials + successes). Pure Python: the t and normal distributions are computed
here, so scipy is not needed.
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


layout = opt("layout", "ROWS")
variant_field = opt("variant_field")
metric_field = opt("metric_field")
trials_field = opt("trials_field")
successes_field = opt("successes_field")
metric_type = opt("metric_type", "CONVERSION")
control = opt("control", "")
segment_fields = opt("segment_fields", []) or []
confidence = float(opt("confidence", 0.95))
power_target = float(opt("power", 0.8))
bonferroni = opt("bonferroni", False)


# ------------------------------------------------------------ distributions
def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p):
    """Acklam's rational approximation (abs error < 1.2e-9)."""
    if p <= 0 or p >= 1:
        return math.copysign(float("inf"), p - 0.5)
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    pl = 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - pl:
        return -norm_ppf(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


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


def t_sf2(t, df):
    """Two-sided p-value for Student's t."""
    if not math.isfinite(t):
        return 0.0
    return betainc(df / 2, 0.5, df / (df + t * t))


def t_ppf(p, df):
    """Quantile of Student's t by bisection on the cdf (p > 0.5)."""
    if df > 1e6:
        return norm_ppf(p)
    lo, hi = 0.0, 1000.0
    target = 2 * (1 - p)
    for _ in range(200):
        mid = (lo + hi) / 2
        if t_sf2(mid, df) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# --------------------------------------------------------------------- data
df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the experiment data to the input.")
if not variant_field or variant_field not in df.columns:
    omniscope_api.abort(f"Choose the variant field (got '{variant_field}').")
need = [metric_field] if layout == "ROWS" else [trials_field, successes_field]
for f in need:
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {'outcome' if layout == 'ROWS' else 'trials and successes'} field(s) that exist in the input (got '{f}').")
if layout == "SUMMARY" and metric_type != "CONVERSION":
    omniscope_api.abort("One row per variant supports conversion rates only (trials and successes).")
miss = [s for s in segment_fields if s not in df.columns]
if miss:
    omniscope_api.abort(f"Segment fields not in the input: {', '.join(miss)}")
if not 0.5 < confidence < 1:
    omniscope_api.abort("Confidence level must be between 0.5 and 1, for example 0.95.")

TRUE = {"1", "1.0", "true", "yes", "y", "converted", "t"}


def outcome(s):
    if metric_type == "CONVERSION":
        if pd.api.types.is_bool_dtype(s):
            return s.astype(float)
        if pd.api.types.is_numeric_dtype(s):
            return (pd.to_numeric(s, errors="coerce") > 0).astype(float).where(s.notna())
        txt = s.astype(str).str.strip().str.lower()
        return txt.isin(TRUE).astype(float).where(s.notna())
    return pd.to_numeric(s, errors="coerce").astype("float64")


work = df.copy()
work["__variant"] = work[variant_field].astype(object).where(work[variant_field].notna(), None).map(lambda v: None if v is None else str(v))
work = work[work["__variant"].notna()]
if layout == "ROWS":
    work["__y"] = outcome(work[metric_field])
    work = work[work["__y"].notna()]
else:
    work["__n"] = pd.to_numeric(work[trials_field], errors="coerce")
    work["__s"] = pd.to_numeric(work[successes_field], errors="coerce")
    work = work[work["__n"].notna() & work["__s"].notna()]

seg_keys = segment_fields or []
segments = [((), work)] if not seg_keys else [((k if isinstance(k, tuple) else (k,)), g) for k, g in work.groupby(seg_keys, sort=True, dropna=False)]


def stats_for(g):
    rows = {}
    for v, sub in g.groupby("__variant", sort=True):
        if layout == "ROWS":
            y = sub["__y"].to_numpy(dtype=float)
            n = len(y)
            m = float(y.mean()) if n else float("nan")
            sd = float(y.std(ddof=1)) if n > 1 else float("nan")
        else:
            n = float(sub["__n"].sum())
            s = float(sub["__s"].sum())
            m = s / n if n else float("nan")
            sd = math.sqrt(m * (1 - m)) if n else float("nan")
        rows[v] = (n, m, sd)
    return rows


alpha_base = 1 - confidence
results, variants_out = [], []
all_variants = list(dict.fromkeys(work["__variant"].tolist()))
ctrl = control if control else (sorted(all_variants)[0] if all_variants else None)
n_comparisons = max(1, (len(all_variants) - 1) * len(segments))
alpha = alpha_base / n_comparisons if bonferroni else alpha_base
z_a = norm_ppf(1 - alpha / 2)
z_b = norm_ppf(power_target)
label = "Conversion Rate" if metric_type == "CONVERSION" else "Mean"

for seg, g in segments:
    st = stats_for(g)
    segd = {f: seg[i] for i, f in enumerate(seg_keys)}
    for v, (n, m, sd) in st.items():
        if metric_type == "CONVERSION":
            se = math.sqrt(m * (1 - m) / n) if n else float("nan")
            z = norm_ppf(1 - alpha_base / 2)
        else:
            se = sd / math.sqrt(n) if n > 1 else float("nan")
            z = t_ppf(1 - alpha_base / 2, n - 1) if n > 1 else float("nan")
        variants_out.append({**segd, "Variant": v, "Is Control": "Yes" if v == ctrl else "No", "Sample Size": n,
                             label: m, "Standard Deviation": sd, "CI Low": m - z * se, "CI High": m + z * se})
    if ctrl not in st:
        continue
    n0, m0, sd0 = st[ctrl]
    for v, (n1, m1, sd1) in st.items():
        if v == ctrl:
            continue
        diff = m1 - m0
        if metric_type == "CONVERSION":
            pool = (m0 * n0 + m1 * n1) / (n0 + n1) if (n0 + n1) else float("nan")
            se_pool = math.sqrt(pool * (1 - pool) * (1 / n0 + 1 / n1)) if n0 and n1 else float("nan")
            stat = diff / se_pool if se_pool and se_pool > 0 else float("nan")
            p = 2 * (1 - norm_cdf(abs(stat))) if math.isfinite(stat) else float("nan")
            se = math.sqrt(m0 * (1 - m0) / n0 + m1 * (1 - m1) / n1) if n0 and n1 else float("nan")
            crit = z_a
            dfree = float("nan")
            var_sum = m0 * (1 - m0) + m1 * (1 - m1)
        else:
            v0, v1 = (sd0 ** 2) / n0 if n0 > 1 else float("nan"), (sd1 ** 2) / n1 if n1 > 1 else float("nan")
            se = math.sqrt(v0 + v1) if math.isfinite(v0 + v1) else float("nan")
            stat = diff / se if se and se > 0 else float("nan")
            dfree = (v0 + v1) ** 2 / (v0 ** 2 / (n0 - 1) + v1 ** 2 / (n1 - 1)) if se and se > 0 else float("nan")
            p = t_sf2(abs(stat), dfree) if math.isfinite(stat) and math.isfinite(dfree) else float("nan")
            crit = t_ppf(1 - alpha / 2, dfree) if math.isfinite(dfree) else float("nan")
            var_sum = sd0 ** 2 + sd1 ** 2
        lift = diff / m0 if m0 else float("nan")
        sig = bool(math.isfinite(p) and p < alpha)
        need_n = math.ceil((z_a + z_b) ** 2 * var_sum / diff ** 2) if diff else float("nan")
        unit = "converts" if metric_type == "CONVERSION" else "averages"
        if not math.isfinite(p):
            verdict = "Not enough data to test."
        elif sig:
            verdict = (f"{v} {unit} {abs(lift):.1%} {'better' if diff > 0 else 'worse'} than {ctrl} "
                       f"(p = {p:.3g}): significant at {confidence:.0%}{' after Bonferroni correction' if bonferroni and n_comparisons > 1 else ''}.")
        else:
            more = f" Roughly {need_n:,} per variant would be needed to confirm a difference this size." if math.isfinite(need_n) else ""
            verdict = f"No significant difference between {v} and {ctrl} (p = {p:.3g}).{more}"
        results.append({**segd, "Variant": v, "Control": ctrl, "Control Size": n0, "Variant Size": n1,
                        f"Control {label}": m0, f"Variant {label}": m1, "Difference": diff, "Relative Lift": lift,
                        "Difference CI Low": diff - crit * se, "Difference CI High": diff + crit * se,
                        "Test Statistic": stat, "Degrees Of Freedom": dfree, "P Value": p,
                        "Significant": "Yes" if sig else "No", "Sample Size Needed Per Variant": need_n,
                        "Verdict": verdict})

res_cols = seg_keys + ["Variant", "Control", "Control Size", "Variant Size", f"Control {label}", f"Variant {label}",
                       "Difference", "Relative Lift", "Difference CI Low", "Difference CI High", "Test Statistic",
                       "Degrees Of Freedom", "P Value", "Significant", "Sample Size Needed Per Variant", "Verdict"]
res = pd.DataFrame(results, columns=res_cols)
for c in res_cols[len(seg_keys) + 2:]:
    if c not in ("Significant", "Verdict"):
        res[c] = pd.to_numeric(res[c], errors="coerce").astype("float64")
for c in ("Control Size", "Variant Size", "Sample Size Needed Per Variant"):
    res[c] = pd.array(np.round(res[c].to_numpy(dtype=float)), dtype="Float64").astype("Int64")
var_cols = seg_keys + ["Variant", "Is Control", "Sample Size", label, "Standard Deviation", "CI Low", "CI High"]
vo = pd.DataFrame(variants_out, columns=var_cols)
for c in (label, "Standard Deviation", "CI Low", "CI High"):
    vo[c] = pd.to_numeric(vo[c], errors="coerce").astype("float64")
vo["Sample Size"] = pd.array(np.round(pd.to_numeric(vo["Sample Size"], errors="coerce").to_numpy(dtype=float)), dtype="Float64").astype("Int64")

omniscope_api.write_output(res, "results")
omniscope_api.write_output(vo, "variants")
if ctrl is not None and ctrl not in all_variants:
    omniscope_api.close(f"Control '{ctrl}' not found among variants {all_variants}; only per-variant statistics produced.")
else:
    n_sig = int((res["Significant"] == "Yes").sum())
    omniscope_api.close(f"{len(res)} comparison(s) against control '{ctrl}': {n_sig} significant at {confidence:.0%}.")
