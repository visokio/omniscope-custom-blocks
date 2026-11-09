"""Regression: linear (least squares) or logistic (binary outcome) regression
with the statistics analysts expect:

  coefficients with standard errors, t or z statistics, p-values and
  confidence intervals (and odds ratios for logistic), variance inflation
  factors for collinearity, overall fit (R-squared, adjusted R-squared, RMSE,
  F test; or log-likelihood, McFadden pseudo R-squared, likelihood-ratio test,
  AUC and accuracy), and every row scored with its prediction.

Text predictors are dummy-coded against their most common value. Rows with a
missing target or predictor are left out of the fit; rows with complete
predictors are still scored.
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


target_f = opt("target_field")
pred_fs = list(opt("predictor_fields", []) or [])
model = opt("model", "AUTO")
positive = opt("positive_class", "")
conf = float(opt("confidence", 0.95))
max_levels = int(opt("max_levels", 30))
threshold = float(opt("threshold", 0.5))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
if not target_f or target_f not in df.columns:
    omniscope_api.abort(f"Choose the target field (got '{target_f}').")
if not pred_fs:
    omniscope_api.abort("Choose at least one predictor field.")
miss = [f for f in pred_fs if f not in df.columns]
if miss:
    omniscope_api.abort(f"Predictor fields not in the input: {', '.join(miss)}")
if target_f in pred_fs:
    omniscope_api.abort("The target cannot also be a predictor.")


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


def f_sf(f, d1, d2):
    if not f == f or f <= 0:
        return 1.0
    return betainc(d2 / 2.0, d1 / 2.0, d2 / (d2 + d1 * f))


def chi2_sf(x, k):
    """Upper tail of chi-square via the regularised incomplete gamma (series / continued fraction)."""
    if x <= 0:
        return 1.0
    a, xx = k / 2.0, x / 2.0
    gln = math.lgamma(a)
    if xx < a + 1:
        ap, s = a, 1.0 / a
        d = s
        for _ in range(2000):
            ap += 1
            d *= xx / ap
            s += d
            if abs(d) < abs(s) * 1e-15:
                break
        return max(0.0, 1.0 - s * math.exp(-xx + a * math.log(xx) - gln))
    b = xx + 1 - a
    c, d = 1e300, 1 / b
    h = d
    for i in range(1, 2000):
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
    return math.exp(-xx + a * math.log(xx) - gln) * h


# ---- design matrix
cols, terms = [], []
X_parts = []
for f in pred_fs:
    s = df[f]
    num = pd.to_numeric(s, errors="coerce") if not pd.api.types.is_bool_dtype(s) else s.astype(float)
    is_num = pd.api.types.is_numeric_dtype(s) or (s.notna().sum() > 0 and num.notna().sum() == s.notna().sum())
    if pd.api.types.is_datetime64_any_dtype(s):
        omniscope_api.abort(f"Predictor '{f}' is a date; use a number derived from it instead (for example days since a start date).")
    if is_num:
        X_parts.append(num.astype("float64").to_numpy()[:, None])
        terms.append((f, None))
    else:
        t = s.astype(object).where(s.notna(), None).map(lambda v: None if v is None else str(v))
        levels = t.dropna().value_counts()
        if len(levels) > max_levels:
            omniscope_api.abort(f"Predictor '{f}' has {len(levels)} distinct values (limit {max_levels}); group it first or raise the limit.")
        if len(levels) < 2:
            omniscope_api.abort(f"Predictor '{f}' has fewer than two distinct values.")
        ref = levels.index[0]
        for lv in sorted(levels.index[1:]):
            col = np.where(t.isna(), np.nan, (t == lv).astype(float))
            X_parts.append(col[:, None])
            terms.append((f, lv))
X = np.hstack(X_parts)
names = ["(Intercept)"] + [f if lv is None else f"{f} = {lv}" for f, lv in terms]
Xf = np.hstack([np.ones((len(df), 1)), X])
complete_x = ~np.isnan(Xf).any(axis=1)

ys = df[target_f]
ynum = pd.to_numeric(ys, errors="coerce")
distinct = ys.dropna().astype(str).unique()
if model == "AUTO":
    model = "LOGISTIC" if len(distinct) == 2 else "LINEAR"
if model == "LOGISTIC":
    if len(distinct) != 2:
        omniscope_api.abort(f"Logistic regression needs a target with exactly two values; '{target_f}' has {len(distinct)}.")
    txt = ys.astype(object).where(ys.notna(), None).map(lambda v: None if v is None else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)))
    vals = sorted(txt.dropna().unique())
    if positive:
        if positive not in vals:
            omniscope_api.abort(f"Positive class '{positive}' is not a value of '{target_f}' (values: {', '.join(vals)}).")
        pos = positive
    else:
        prefer = [v for v in vals if v.strip().lower() in ("1", "yes", "y", "true", "churned", "converted", "won", "default", "positive")]
        pos = prefer[0] if prefer else vals[-1]
    y = np.where(txt.isna(), np.nan, (txt == pos).astype(float))
else:
    if ynum.notna().sum() == 0:
        omniscope_api.abort(f"Linear regression needs a numeric target; '{target_f}' has no numbers.")
    y = ynum.astype("float64").to_numpy()
fit_rows = complete_x & ~np.isnan(y)
Xm, yv = Xf[fit_rows], y[fit_rows]
n, k = Xm.shape
if n <= k:
    omniscope_api.abort(f"Too few complete rows ({n}) for {k} coefficients.")
rank = np.linalg.matrix_rank(Xm)
if rank < k:
    # name the first term that is a linear combination of earlier ones
    for j in range(2, k + 1):
        if np.linalg.matrix_rank(Xm[:, :j]) < j:
            omniscope_api.abort(f"'{names[j - 1]}' is perfectly collinear with earlier terms (for example a duplicate field, or levels that always go together). Remove it.")


def vif(Xm):
    out = [np.nan]
    for j in range(1, Xm.shape[1]):
        others = np.delete(Xm, j, axis=1)
        beta, *_ = np.linalg.lstsq(others, Xm[:, j], rcond=None)
        r = Xm[:, j] - others @ beta
        ss_tot = ((Xm[:, j] - Xm[:, j].mean()) ** 2).sum()
        r2 = 1 - (r @ r) / ss_tot if ss_tot > 0 else 1.0
        out.append(1 / (1 - r2) if r2 < 1 else np.inf)
    return out


V = vif(Xm) if k > 2 else [np.nan] + [1.0] * (k - 1)
coef_rows = []
fitstats = []
scored = df.copy()
if model == "LINEAR":
    XtX_inv = np.linalg.inv(Xm.T @ Xm)
    beta = XtX_inv @ Xm.T @ yv
    resid = yv - Xm @ beta
    dfree = n - k
    sse = float(resid @ resid)
    sigma2 = sse / dfree
    se = np.sqrt(np.diag(XtX_inv) * sigma2)
    tcrit = t_ppf(1 - (1 - conf) / 2, dfree)
    tstat = beta / se
    pv = [t_sf2(abs(t), dfree) for t in tstat]
    sst = float(((yv - yv.mean()) ** 2).sum())
    r2 = 1 - sse / sst if sst > 0 else np.nan
    adj = 1 - (1 - r2) * (n - 1) / dfree if sst > 0 else np.nan
    fstat = ((sst - sse) / (k - 1)) / sigma2 if k > 1 and sigma2 > 0 else np.nan
    for j, nm in enumerate(names):
        coef_rows.append({"Term": nm, "Field": "(Intercept)" if j == 0 else terms[j - 1][0], "Level": None if j == 0 else terms[j - 1][1],
                          "Coefficient": beta[j], "Std Error": se[j], "t or z": tstat[j], "P Value": pv[j],
                          "CI Low": beta[j] - tcrit * se[j], "CI High": beta[j] + tcrit * se[j], "VIF": V[j]})
    fitstats = [("Model", "Linear regression (least squares)"), ("Rows used", n), ("Rows left out (missing values)", int(len(df) - n)),
                ("Coefficients", k), ("R-squared", r2), ("Adjusted R-squared", adj), ("RMSE", math.sqrt(sse / n)),
                ("Residual standard error", math.sqrt(sigma2)), ("F statistic", fstat), ("F test p-value", f_sf(fstat, k - 1, dfree)),
                ("Log-likelihood", -n / 2 * (math.log(2 * math.pi) + math.log(sse / n) + 1)),
                ("AIC", n * (math.log(2 * math.pi) + math.log(sse / n) + 1) + 2 * k)]  # same convention as statsmodels
    pred = np.where(complete_x, np.nan_to_num(Xf) @ beta, np.nan)
    scored["Prediction"] = pred
    scored["Residual"] = np.where(~np.isnan(y) & complete_x, y - pred, np.nan)
    scored["Prediction Low"] = pred - tcrit * np.sqrt(sigma2 + np.einsum("ij,jk,ik->i", np.nan_to_num(Xf), XtX_inv * sigma2, np.nan_to_num(Xf)))
    scored["Prediction High"] = 2 * pred - scored["Prediction Low"]
    scored.loc[~complete_x, ["Prediction Low", "Prediction High"]] = np.nan
else:
    beta = np.zeros(k)
    p0 = yv.mean()
    beta[0] = math.log(p0 / (1 - p0)) if 0 < p0 < 1 else 0.0
    separated = False
    for it in range(100):
        eta = np.clip(Xm @ beta, -35, 35)
        mu = 1 / (1 + np.exp(-eta))
        W = mu * (1 - mu)
        H = Xm.T @ (Xm * W[:, None])
        g = Xm.T @ (yv - mu)
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, g, rcond=None)[0]
        beta = beta + step
        if np.max(np.abs(step)) < 1e-9:
            break
        if np.max(np.abs(beta)) > 30:
            separated = True
            break
    eta = np.clip(Xm @ beta, -35, 35)
    mu = 1 / (1 + np.exp(-eta))
    W = mu * (1 - mu)
    cov = np.linalg.pinv(Xm.T @ (Xm * W[:, None]))
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    zcrit = norm_ppf(1 - (1 - conf) / 2)
    zstat = beta / np.where(se > 0, se, np.nan)
    pv = [2 * (1 - norm_cdf(abs(z))) if z == z else np.nan for z in zstat]
    ll = float((yv * np.log(np.clip(mu, 1e-15, 1)) + (1 - yv) * np.log(np.clip(1 - mu, 1e-15, 1))).sum())
    ll0 = float(n * (p0 * math.log(p0) + (1 - p0) * math.log(1 - p0))) if 0 < p0 < 1 else 0.0
    lr = 2 * (ll - ll0)
    # AUC from the Mann-Whitney statistic, with average ranks for ties
    s_mu = pd.Series(mu).rank(method="average").to_numpy()
    npos = yv.sum()
    auc = (s_mu[yv == 1].sum() - npos * (npos + 1) / 2) / (npos * (n - npos)) if 0 < npos < n else np.nan
    acc = float(((mu >= threshold) == (yv == 1)).mean())
    for j, nm in enumerate(names):
        coef_rows.append({"Term": nm, "Field": "(Intercept)" if j == 0 else terms[j - 1][0], "Level": None if j == 0 else terms[j - 1][1],
                          "Coefficient": beta[j], "Std Error": se[j], "t or z": zstat[j], "P Value": pv[j],
                          "CI Low": beta[j] - zcrit * se[j], "CI High": beta[j] + zcrit * se[j], "VIF": V[j],
                          "Odds Ratio": math.exp(beta[j]) if abs(beta[j]) < 700 else np.nan,
                          "Odds Ratio CI Low": math.exp(beta[j] - zcrit * se[j]) if abs(beta[j]) < 700 else np.nan,
                          "Odds Ratio CI High": math.exp(beta[j] + zcrit * se[j]) if abs(beta[j]) < 700 else np.nan})
    fitstats = [("Model", "Logistic regression (maximum likelihood)"), ("Positive class", pos), ("Rows used", n),
                ("Rows left out (missing values)", int(len(df) - n)), ("Coefficients", k), ("Positive share", p0),
                ("Log-likelihood", ll), ("Null log-likelihood", ll0), ("McFadden pseudo R-squared", 1 - ll / ll0 if ll0 else np.nan),
                ("Likelihood-ratio chi-square", lr), ("Likelihood-ratio p-value", chi2_sf(lr, k - 1)), ("AIC", -2 * ll + 2 * k),
                ("AUC", auc), (f"Accuracy at threshold {threshold:g}", acc)]
    if separated:
        fitstats.append(("Warning", "Coefficients grew very large: the classes may be perfectly separated by a predictor; treat estimates with care."))
    prob = np.where(complete_x, 1 / (1 + np.exp(-np.clip(np.nan_to_num(Xf) @ beta, -35, 35))), np.nan)
    scored["Probability"] = prob
    scored["Predicted Class"] = np.where(np.isnan(prob), None, np.where(prob >= threshold, pos, "Not " + pos))
coef = pd.DataFrame(coef_rows)
coef["Significant"] = np.where(coef["P Value"] < 1 - conf, "Yes", "No")
for c in coef.columns:
    if c not in ("Term", "Field", "Level", "Significant"):
        coef[c] = coef[c].astype("float64")
fit = pd.DataFrame({"Statistic": [a for a, _ in fitstats],
                    "Value": [float(b) if isinstance(b, (int, float, np.floating, np.integer)) and not isinstance(b, bool) else np.nan for _, b in fitstats],
                    "Text": [b if isinstance(b, str) else None for _, b in fitstats]})
fit["Value"] = fit["Value"].astype("float64")
for c in ("Prediction", "Residual", "Prediction Low", "Prediction High", "Probability"):
    if c in scored:
        scored[c] = scored[c].astype("float64")
scored["Used In Fit"] = np.where(fit_rows, "Yes", "No")

omniscope_api.write_output(coef, "coefficients")
omniscope_api.write_output(fit, "fit")
omniscope_api.write_output(scored, "scored")
fs = dict(fitstats)
if model == "LINEAR":
    msg = f"Linear regression on {n:,} rows: R-squared {fs['R-squared']:.3f}, {int((coef['Significant'] == 'Yes').sum()) - (1 if coef['Significant'].iloc[0] == 'Yes' else 0)} of {k - 1} terms significant"
else:
    msg = f"Logistic regression on {n:,} rows (positive class '{pos}'): AUC {fs['AUC']:.3f}, pseudo R-squared {fs['McFadden pseudo R-squared']:.3f}"
high_vif = [names[j] for j in range(1, k) if V[j] == V[j] and V[j] > 10]
omniscope_api.close(msg + (f"; high collinearity (VIF > 10): {', '.join(high_vif[:3])}" if high_vif else "") + ".")
