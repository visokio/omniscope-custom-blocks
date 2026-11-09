"""Net Promoter Score: from 0-10 "how likely are you to recommend" answers,
calculate per group (and optionally per period)

  promoters (9-10), passives (7-8) and detractors (0-6), counts and shares,
  NPS = % promoters - % detractors (-100 to +100),
  its standard error, margin of error and confidence interval
  (variance of the +1 / 0 / -1 score), with optional survey weights
  (effective sample size from the weights),
  whether each group differs significantly from the rest, and the change from
  the previous period with its significance.

Also a score distribution (0 to 10) per group, and the responses with their
category and NPS points (+100 / 0 / -100) so NPS can be re-aggregated anywhere.
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


score_f = opt("score_field")
group_fields = opt("group_fields", []) or []
date_f = opt("date_field")
period = opt("period", "NONE")
weight_f = opt("weight_field")
conf = float(opt("confidence", 0.95))
min_n = int(opt("min_responses", 30) or 0)
FREQ = {"MONTH": "M", "QUARTER": "Q", "YEAR": "Y"}

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the survey responses to the input.")
if not score_f or score_f not in df.columns:
    omniscope_api.abort(f"Choose the score field (got '{score_f}').")
miss = [f for f in list(group_fields) + [x for x in (date_f, weight_f) if x] if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")
if period != "NONE" and not date_f:
    omniscope_api.abort("Choose the date field to report by period, or set the period to None.")
if not 0.5 <= conf < 1:
    omniscope_api.abort("Confidence level must be between 0.5 and 0.999, for example 0.95.")


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


Z = norm_ppf(1 - (1 - conf) / 2)


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
    return d


score = pd.to_numeric(df[score_f], errors="coerce").astype("float64")
valid = score.notna() & (score >= 0) & (score <= 10) & (score == score.round())
invalid = int((~valid & df[score_f].notna()).sum())
blank = int(df[score_f].isna().sum())
wt = pd.to_numeric(df[weight_f], errors="coerce").astype("float64") if weight_f else pd.Series(1.0, index=df.index)
valid &= wt.notna() & (wt > 0)
cat = pd.Series(np.select([score >= 9, score >= 7], ["Promoter", "Passive"], "Detractor"), index=df.index).where(valid, None)
pts = pd.Series(np.select([score >= 9, score >= 7], [100.0, 0.0], -100.0), index=df.index).where(valid, np.nan)

w = pd.DataFrame({"s": score, "w": wt, "x": pts / 100.0})
for g in group_fields:
    w[g] = df[g].astype(object).where(df[g].notna(), "(blank)").map(str)
if period != "NONE":
    dts = to_date(df[date_f])
    w["Period"] = dts.dt.to_period(FREQ[period]).astype(str).where(dts.notna(), None)
    valid &= dts.notna()
w = w[valid]
pcol = ["Period"] if period != "NONE" else []


def stats(g):
    wv, x = g["w"].to_numpy(), g["x"].to_numpy()
    n = len(g)
    sw = wv.sum()
    if n == 0 or sw <= 0:
        return {"Responses": n}
    n_eff = sw ** 2 / (wv ** 2).sum()
    p = wv[x > 0].sum() / sw
    d = wv[x < 0].sum() / sw
    nps = p - d
    var = max(p + d - nps ** 2, 0.0)
    se = 100 * math.sqrt(var / n_eff) if n_eff > 1 else np.nan
    return {"Responses": n, "Effective Sample Size": n_eff, "Promoters": int((x > 0).sum()), "Passives": int((x == 0).sum()),
            "Detractors": int((x < 0).sum()), "% Promoters": 100 * p, "% Passives": 100 * (1 - p - d), "% Detractors": 100 * d,
            "NPS": 100 * nps, "Standard Error": se, "Margin Of Error": Z * se if se == se else np.nan,
            "CI Low": 100 * nps - Z * se if se == se else np.nan, "CI High": 100 * nps + Z * se if se == se else np.nan,
            "Average Score": float((g["s"].to_numpy() * wv).sum() / sw)}


def sig(diff, se):
    if se != se:
        return "Not tested"
    if se == 0:  # no variation in either group: any difference is certain
        return "Not significant" if diff == 0 else ("Higher" if diff > 0 else "Lower")
    return ("Higher" if diff > 0 else "Lower") if abs(diff) / se > Z else "Not significant"


rows = []
for pk, pg in (w.groupby(pcol, sort=True) if pcol else [((), w)]):
    pk = pk if isinstance(pk, tuple) else (pk,)
    base = dict(zip(pcol, pk))
    tot = stats(pg)
    rows.append({**{g: "All" for g in group_fields}, **base, **tot, "Vs Rest": None})
    if group_fields:
        for gk, gg in pg.groupby(group_fields, sort=True):
            gk = gk if isinstance(gk, tuple) else (gk,)
            st = stats(gg)
            rest = stats(pg.drop(gg.index))
            v = "Not tested"
            if "NPS" in st and "NPS" in rest:
                v = sig(st["NPS"] - rest["NPS"], math.sqrt(st["Standard Error"] ** 2 + rest["Standard Error"] ** 2)
                        if st["Standard Error"] == st["Standard Error"] and rest["Standard Error"] == rest["Standard Error"] else np.nan)
                st["Difference Vs Rest"] = st["NPS"] - rest["NPS"]
            rows.append({**dict(zip(group_fields, gk)), **base, **st, "Vs Rest": v})
NUM = ["Effective Sample Size", "% Promoters", "% Passives", "% Detractors", "NPS", "Standard Error", "Margin Of Error", "CI Low", "CI High",
       "Average Score", "Difference Vs Rest"]
cols = list(group_fields) + pcol + ["Responses", "Effective Sample Size", "Promoters", "Passives", "Detractors", "% Promoters", "% Passives",
                                    "% Detractors", "NPS", "Standard Error", "Margin Of Error", "CI Low", "CI High", "Average Score",
                                    "Difference Vs Rest", "Vs Rest"]
summ = pd.DataFrame(rows, columns=cols)
if pcol and len(summ):
    keycols = list(group_fields)
    summ = summ.sort_values(keycols + pcol, kind="mergesort") if keycols else summ.sort_values(pcol, kind="mergesort")
    grp = summ.groupby(keycols, sort=False) if keycols else summ.groupby(lambda _: 0)
    summ["Previous NPS"] = grp["NPS"].shift(1)
    prev_se = grp["Standard Error"].shift(1)
    summ["Change Vs Previous"] = summ["NPS"] - summ["Previous NPS"]
    se_c = np.sqrt(summ["Standard Error"] ** 2 + prev_se ** 2)
    summ["Change Significant"] = [(None if c != c else sig(c, s)) for c, s in zip(summ["Change Vs Previous"], se_c)]
    summ = summ.reset_index(drop=True)
summ["Small Sample"] = np.where(summ["Responses"] < min_n, "Yes", "No")
for c in ("Responses", "Promoters", "Passives", "Detractors"):
    summ[c] = summ[c].fillna(0).astype("int64")
for c in NUM + (["Previous NPS", "Change Vs Previous"] if pcol else []):
    summ[c] = summ[c].astype("float64")

# distribution 0..10
dist_rows = []
keys = list(group_fields)
parts = [(("All",) * len(keys), w)] + ([((k if isinstance(k, tuple) else (k,)), g) for k, g in w.groupby(keys, sort=True)] if keys else [])
for k, g in parts:
    sw = g["w"].sum()
    by = g.groupby("s")["w"].agg(["sum", "size"])
    for sc in range(11):
        s_w, s_n = (float(by.loc[sc, "sum"]), int(by.loc[sc, "size"])) if sc in by.index else (0.0, 0)
        dist_rows.append({**dict(zip(keys, k)), "Score": sc, "Category": "Promoter" if sc >= 9 else "Passive" if sc >= 7 else "Detractor",
                          "Responses": s_n, "Share": (s_w / sw) if sw else np.nan})
dist = pd.DataFrame(dist_rows, columns=keys + ["Score", "Category", "Responses", "Share"])
dist["Score"] = dist["Score"].astype("int64")
dist["Responses"] = dist["Responses"].astype("int64")
dist["Share"] = dist["Share"].astype("float64")

resp = df.copy()
resp["NPS Category"] = cat.astype(object)
resp["NPS Points"] = pts.astype("float64")

omniscope_api.write_output(summ, "nps")
omniscope_api.write_output(dist, "distribution")
omniscope_api.write_output(resp, "responses")
overall = summ[(summ[group_fields] == "All").all(axis=1)] if group_fields else summ
msg = f"{int(valid.sum()):,} valid responses"
if len(overall) and "NPS" in overall and overall["NPS"].notna().any():
    last = overall.iloc[-1]
    msg += f"; NPS {last['NPS']:+.1f} (±{last['Margin Of Error']:.1f} at {conf:.0%})" + (f" in {last['Period']}" if pcol else "")
skip = []
if blank:
    skip.append(f"{blank:,} blank")
if invalid:
    skip.append(f"{invalid:,} not a whole number from 0 to 10")
omniscope_api.close(msg + (f"; skipped {', '.join(skip)}" if skip else "") + ".")
