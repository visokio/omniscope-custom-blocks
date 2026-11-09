"""Inflation Adjustment: restate money values in real terms (the prices of a
base period) using a price index table such as a consumer or producer price
index, optionally per country or index series.

Each row takes the index in force at its date (the latest index period on or
before it); real value = nominal value x index at base / index at the row's
date. The base period is chosen in the options (default: the latest index
period). Outputs: the rows with the index used and the real values, and the
index table with cumulative inflation to the base period.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


date_f = opt("date_field")
values = list(opt("value_fields", []) or [])
key_f = opt("key_field")
i_date, i_val, i_key = opt("index_date_field"), opt("index_value_field"), opt("index_key_field")
base_txt = opt("base_period", "")
suffix = opt("suffix", " (real)")
max_age = int(opt("max_age_days", 400))

D = omniscope_api.read_input_records(input_number=0)
X = omniscope_api.read_input_records(input_number=1)
if D is None or X is None:
    omniscope_api.abort("Connect the values to input 1 and the price index table to input 2.")
if not date_f or date_f not in D.columns:
    omniscope_api.abort(f"Choose the date field of input 1 (got '{date_f}').")
if not values:
    omniscope_api.abort("Choose at least one money field to adjust.")
miss = [f for f in values + ([key_f] if key_f else []) if f not in D.columns]
if miss:
    omniscope_api.abort(f"Fields not in input 1: {', '.join(miss)}")
for f, lab in ((i_date, "index date"), (i_val, "index value")):
    if not f or f not in X.columns:
        omniscope_api.abort(f"Choose the {lab} field of input 2 (got '{f}').")
if i_key and i_key not in X.columns:
    omniscope_api.abort(f"Field '{i_key}' is not in input 2.")
if bool(key_f) != bool(i_key):
    omniscope_api.abort("Choose a key (for example Country) on both inputs, or on neither.")


def to_date(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s
    else:
        txt = s.astype(object).where(s.notna(), None).astype(str).str.strip()
        txt = txt.where(~txt.str.fullmatch(r"\d{4}-\d{1,2}"), txt + "-01")  # "2024-03" means the month
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        d = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        d[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
        d[~iso & s.notna()] = pd.to_datetime(txt[~iso & s.notna()], errors="coerce", dayfirst=True, format="mixed")
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    return d.astype("datetime64[ns]")


keyfun = lambda s: s.astype(object).where(s.notna(), "(blank)").map(str)
ix = pd.DataFrame({"t": to_date(X[i_date]), "v": pd.to_numeric(X[i_val], errors="coerce").astype("float64"),
                   "k": keyfun(X[i_key]) if i_key else "*"}).dropna(subset=["t", "v"])
if (ix["v"] <= 0).any():
    omniscope_api.abort("Index values must be positive.")
if ix.empty:
    omniscope_api.abort("The index table has no valid dates and values.")
ix = ix.sort_values(["k", "t"]).drop_duplicates(["k", "t"], keep="last")
if base_txt:
    base_t = to_date(pd.Series([base_txt], dtype=object)).iloc[0]
    if pd.isna(base_t):
        omniscope_api.abort("The base period must be a date or a month, such as 2025-06.")
else:
    base_t = ix["t"].max()
base_val = {}
for k, g in ix.groupby("k"):
    b = g[g["t"] <= base_t]
    if b.empty:
        omniscope_api.abort(f"No index value on or before the base period {base_t.date()} for '{k}'.")
    base_val[k] = float(b["v"].iloc[-1])

w = pd.DataFrame({"t": to_date(D[date_f]), "k": keyfun(D[key_f]) if key_f else "*", "row": np.arange(len(D))})
ok = w["t"].notna()
m = pd.merge_asof(w[ok].sort_values("t"), ix.rename(columns={"t": "ti"}).sort_values("ti"), left_on="t", right_on="ti", by="k", direction="backward")
m = m.set_index("row").reindex(np.arange(len(D)))
age = (m["t"] - m["ti"]).dt.days
idx_at = m["v"].where(age <= max_age)
base_at = w["k"].map(base_val)
factor = (base_at / idx_at).astype("float64")
out = D.copy()
out["Index Period Used"] = pd.to_datetime(m["ti"].where(age <= max_age)).dt.tz_localize("UTC").to_numpy()
out["Index At Date"] = idx_at.astype("float64").to_numpy()
out["Index At Base"] = base_at.astype("float64").to_numpy()
out["Inflation Factor"] = factor.to_numpy()
for f in values:
    out[f + suffix] = (pd.to_numeric(D[f], errors="coerce").astype("float64") * factor).to_numpy()
status = np.where(~ok.to_numpy(), "No date", np.where(m["ti"].isna().to_numpy(), "No index on or before date", np.where((age > max_age).to_numpy(), "Index too old", "Adjusted")))
out["Adjustment Status"] = status
tab = ix.copy()
tab["Index At Base"] = tab["k"].map(base_val)
tab["Inflation To Base"] = tab["Index At Base"] / tab["v"] - 1
tab["Change From Previous"] = tab.groupby("k")["v"].pct_change()
tab["Change From Year Before"] = [np.nan] * len(tab)
for k, g in tab.groupby("k"):
    s = g.set_index("t")["v"]
    prev = s.reindex(g["t"] - pd.DateOffset(years=1)).to_numpy()
    tab.loc[g.index, "Change From Year Before"] = g["v"].to_numpy() / prev - 1
tab = tab.rename(columns={"t": "Index Period", "v": "Index Value", "k": "Key"})
tab["Index Period"] = pd.to_datetime(tab["Index Period"]).dt.tz_localize("UTC")
if not i_key:
    tab = tab.drop(columns=["Key"])
for c in ("Index Value", "Index At Base", "Inflation To Base", "Change From Previous", "Change From Year Before"):
    tab[c] = tab[c].astype("float64")
omniscope_api.write_output(out, "rows")
omniscope_api.write_output(tab.reset_index(drop=True), "index")
n_ok = int((status == "Adjusted").sum())
omniscope_api.close(f"{n_ok:,} of {len(out):,} rows restated in {base_t.strftime('%Y-%m')} prices" + (f"; {len(out) - n_ok:,} not adjusted (see Adjustment Status)" if n_ok < len(out) else "") + ".")
