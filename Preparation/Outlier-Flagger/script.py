"""Outlier Flagger: flag unusually low or high values in many numeric fields at
once, optionally within groups (per product, region, machine), by one of
three standard rules:

  IQR      outside Q1 - k x IQR .. Q3 + k x IQR (Tukey's fences, k = 1.5)
  Z-score  more than k standard deviations from the mean (k = 3)
  MAD      robust z = 0.6745 x (x - median) / MAD above k (k = 3.5, Iglewicz and Hoaglin)

Groups smaller than the minimum size are not tested. Outputs: the rows with
an outlier flag per field and a count, one row per outlier with its bound and
score, and the bounds used per field and group. Optionally, outliers can be
capped at the bounds (winsorised) in extra fields.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


fields = list(opt("fields", []) or [])
group_fields = list(opt("group_fields", []) or [])
method = opt("method", "IQR")
k_opt = opt("k")
k = float(k_opt) if k_opt not in (None, "", 0, 0.0) else {"IQR": 1.5, "ZSCORE": 3.0, "MAD": 3.5}[method]
min_n = int(opt("min_group_size", 10))
cap = bool(opt("add_capped", False))
key_fields = list(opt("key_fields", []) or [])

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
df = df.reset_index(drop=True)
miss = [f for f in fields + group_fields + key_fields if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")
if not fields:
    fields = [c for c in df.columns if c not in group_fields and c not in key_fields and pd.api.types.is_numeric_dtype(df[c])
              and not pd.api.types.is_bool_dtype(df[c])]
if not fields:
    omniscope_api.abort("No numeric fields to check; choose the fields.")
if k <= 0:
    omniscope_api.abort("The multiplier must be above zero.")
X = {f: pd.to_numeric(df[f], errors="coerce").astype("float64") for f in fields}
bad = [f for f in fields if df[f].notna().any() and X[f].isna().all()]
if bad:
    omniscope_api.abort(f"Fields must be numeric: {', '.join(bad)}")

gkey = pd.Series(["All"] * len(df), index=df.index) if not group_fields else \
    df[group_fields].astype(object).where(df[group_fields].notna(), "(blank)").astype(str).agg(" | ".join, axis=1)
flags = {f: np.full(len(df), None, dtype=object) for f in fields}
scores = {f: np.full(len(df), np.nan) for f in fields}
capped = {f: X[f].to_numpy().copy() for f in fields}
brows, orows = [], []
pos_of = {ix: i for i, ix in enumerate(df.index)}
for g, idx in gkey.groupby(gkey, sort=True).groups.items():
    pos = np.array([pos_of[i] for i in idx])
    gvals = df.loc[idx, group_fields].iloc[0].tolist() if group_fields else []
    for f in fields:
        v = X[f].to_numpy()[pos]
        ok = ~np.isnan(v)
        vv = v[ok]
        rec = {**dict(zip(group_fields, gvals)), "Field": f, "Values": int(ok.sum())}
        if len(vv) < max(min_n, 3):
            rec.update({"Tested": "No (too few values)"})
            brows.append(rec)
            continue
        if method == "IQR":
            q1, q3 = np.percentile(vv, [25, 75])
            iqr = q3 - q1
            lo, hi = q1 - k * iqr, q3 + k * iqr
            if iqr > 0:
                sc = np.where(v > q3, (v - q3) / iqr, np.where(v < q1, (v - q1) / iqr, 0.0))  # IQRs beyond the quartile
            else:
                sc = np.where(v > q3, np.inf, np.where(v < q1, -np.inf, 0.0))
        elif method == "ZSCORE":
            mu, sd = vv.mean(), vv.std(ddof=1)
            lo, hi = mu - k * sd, mu + k * sd
            sc = (v - mu) / sd if sd > 0 else np.zeros_like(v)
        else:
            med = np.median(vv)
            mad = np.median(np.abs(vv - med))
            lo, hi = (med - k * mad / 0.6745, med + k * mad / 0.6745) if mad > 0 else (med, med)
            sc = 0.6745 * (v - med) / mad if mad > 0 else np.where(v == med, 0.0, np.sign(v - med) * np.inf)
        low, high = ok & (v < lo), ok & (v > hi)
        fl = np.where(high, "High", np.where(low, "Low", np.where(ok, "No", None)))
        flags[f][pos] = fl
        scores[f][pos] = np.where(ok, sc, np.nan)
        capped[f][pos] = np.where(ok, np.clip(v, lo, hi), np.nan)
        rec.update({"Tested": "Yes", "Method": method, "Multiplier": k, "Lower Bound": float(lo), "Upper Bound": float(hi),
                    "Low Outliers": int(low.sum()), "High Outliers": int(high.sum()), "Outlier Share": float((low | high).sum() / ok.sum()),
                    "Minimum": float(vv.min()), "Median": float(np.median(vv)), "Maximum": float(vv.max())})
        brows.append(rec)
        for i in np.nonzero(low | high)[0]:
            r = pos[i]
            orows.append({"Row Number": int(r) + 1, **{kf: df[kf].iloc[r] for kf in key_fields}, **dict(zip(group_fields, gvals)), "Field": f,
                          "Value": float(v[i]), "Direction": "High" if high[i] else "Low", "Bound": float(hi if high[i] else lo),
                          "Score": float(sc[i]) if np.isfinite(sc[i]) else np.nan, "Beyond Bound": float(v[i] - (hi if high[i] else lo))})

bcols = group_fields + ["Field", "Values", "Tested", "Method", "Multiplier", "Lower Bound", "Upper Bound", "Low Outliers", "High Outliers", "Outlier Share",
                        "Minimum", "Median", "Maximum"]
bounds = pd.DataFrame(brows, columns=bcols)
bounds["Values"] = bounds["Values"].astype("int64")
for c in ("Low Outliers", "High Outliers"):
    bounds[c] = pd.array(pd.to_numeric(bounds[c]).to_numpy(dtype=float), dtype="Float64").astype("Int64")
for c in ("Multiplier", "Lower Bound", "Upper Bound", "Outlier Share", "Minimum", "Median", "Maximum"):
    bounds[c] = bounds[c].astype("float64")
ocols = ["Row Number"] + key_fields + group_fields + ["Field", "Value", "Direction", "Bound", "Score", "Beyond Bound"]
outl = pd.DataFrame(orows, columns=ocols).sort_values(["Row Number", "Field"], kind="mergesort").reset_index(drop=True)
outl["Row Number"] = outl["Row Number"].astype("int64")
for c in ("Value", "Bound", "Score", "Beyond Bound"):
    outl[c] = outl[c].astype("float64")

rows = df.copy()
cnt = np.zeros(len(df), dtype=int)
names = [[] for _ in range(len(df))]
for f in fields:
    rows[f"{f} Outlier"] = flags[f]
    hit = np.isin(flags[f].astype(str), ["High", "Low"])
    cnt += hit
    for i in np.nonzero(hit)[0]:
        names[i].append(f"{f} ({flags[f][i].lower()})")
    if cap:
        rows[f"{f} Capped"] = capped[f].astype("float64")
rows["Outlier Count"] = cnt.astype("int64")
rows["Outlier Fields"] = ["; ".join(x) if x else None for x in names]

omniscope_api.write_output(rows, "rows")
omniscope_api.write_output(outl, "outliers")
omniscope_api.write_output(bounds, "bounds")
omniscope_api.close(f"{len(fields)} field(s), {gkey.nunique():,} group(s), {method} with multiplier {k:g}: {len(outl):,} outlying values in {int((cnt > 0).sum()):,} rows"
                    + (f"; {int((bounds['Tested'] != 'Yes').sum()):,} field-group combinations had too few values to test" if (bounds['Tested'] != 'Yes').any() else "") + ".")
