"""As-Of Join: for each row of input 1, attach the row of input 2 that was in
force at that row's date, per key: the latest exchange rate on or before the
transaction date, the price list effective at the order date, the tariff,
owner, grade or address valid at the time.

Direction: latest on or before (default), next on or after, or nearest.
Optional: a maximum gap in days (older records do not count), an end-date field
on input 2 for validity ranges (valid from / valid to), and which input 2
fields to bring across. Every input 1 row is kept, in its original order,
with the matched date, the gap in days and a status.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


lkeys = list(opt("left_keys", []) or [])
rkeys = list(opt("right_keys", []) or [])
ldate = opt("left_date")
rdate = opt("right_date")
rend = opt("right_end_date")
direction = opt("direction", "BACKWARD")
max_gap = float(opt("max_gap_days", 0) or 0)
add_fields = list(opt("fields_to_add", []) or [])
suffix = opt("suffix", " (as of)")

L = omniscope_api.read_input_records(input_number=0)
R = omniscope_api.read_input_records(input_number=1)
if L is None or R is None:
    omniscope_api.abort("Connect the rows to look up for to input 1 and the dated reference table to input 2.")
if not ldate or ldate not in L.columns:
    omniscope_api.abort(f"Choose the date field of input 1 (got '{ldate}').")
if not rdate or rdate not in R.columns:
    omniscope_api.abort(f"Choose the effective date field of input 2 (got '{rdate}').")
if rend and rend not in R.columns:
    omniscope_api.abort(f"End date field '{rend}' is not in input 2.")
if not rkeys:
    rkeys = [k for k in lkeys if k in R.columns] if lkeys else []
if len(lkeys) != len(rkeys):
    omniscope_api.abort(f"Choose the same number of key fields on both sides ({len(lkeys)} on input 1, {len(rkeys)} on input 2), matched in order.")
for f in lkeys:
    if f not in L.columns:
        omniscope_api.abort(f"Key field '{f}' is not in input 1.")
for f in rkeys + add_fields:
    if f not in R.columns:
        omniscope_api.abort(f"Field '{f}' is not in input 2.")
if not add_fields:
    add_fields = [c for c in R.columns if c not in rkeys and c != rdate and c != rend]


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


def key_text(s):
    t = s.astype(object).where(s.notna(), None)
    return t.map(lambda v: "\u0000null" if v is None else (str(int(v)) if isinstance(v, float) and v.is_integer() else str(v).strip()))


KN = [f"__k{i}" for i in range(len(lkeys))]
lw = pd.DataFrame({"__row": np.arange(len(L)), "__t": to_date(L[ldate]).to_numpy()})
for i, k in enumerate(lkeys):
    lw[KN[i]] = key_text(L[k]).to_numpy()
rw = pd.DataFrame({"__rrow": np.arange(len(R)), "__t": to_date(R[rdate]).to_numpy()})
for i, k in enumerate(rkeys):
    rw[KN[i]] = key_text(R[k]).to_numpy()
r_bad = int(rw["__t"].isna().sum())
rw = rw.dropna(subset=["__t"])
rw["__rt"] = rw["__t"]
l_ok = lw["__t"].notna()

res = pd.DataFrame({"__row": lw["__row"], "__rrow": np.nan, "__rt": pd.NaT}).set_index("__row")
if l_ok.any() and len(rw):
    lsort = lw[l_ok].sort_values("__t", kind="mergesort")
    rsort = rw.sort_values(["__t", "__rrow"], kind="mergesort")
    # the latest row wins among several with the same date and key
    rsort = rsort.drop_duplicates(subset=KN + ["__t"], keep="last")
    kw = {"by": KN} if KN else {}
    if max_gap > 0:
        kw["tolerance"] = pd.Timedelta(days=max_gap)
    m = pd.merge_asof(lsort, rsort[["__t", "__rt", "__rrow"] + KN], on="__t", direction=direction.lower(), allow_exact_matches=True, **kw)
    m = m.set_index("__row")
    res.loc[m.index, "__rrow"] = m["__rrow"].to_numpy()
    res.loc[m.index, "__rt"] = m["__rt"].to_numpy()

rr = res["__rrow"].to_numpy()
has = ~np.isnan(rr)
ltime = lw["__t"].to_numpy()
rtime = res["__rt"].to_numpy(dtype="datetime64[ns]")
status = np.full(len(L), "Matched", dtype=object)
status[~l_ok.to_numpy()] = "No date"
status[l_ok.to_numpy() & ~has] = "No record in range"
if rend and has.any():
    ends = to_date(R[rend]).to_numpy()
    idx = np.nonzero(has)[0]
    e = ends[rr[idx].astype(int)]
    expired = ~pd.isna(e) & (ltime[idx] > e)
    status[idx[expired]] = "Expired (after end date)"
    has[idx[expired]] = False

out = L.copy()
conflict = set(out.columns)
take = rr.copy()
take[~has] = -1
for f in add_fields:
    col = R[f].reset_index(drop=True)
    vals = col.reindex(take.astype(int)).reset_index(drop=True) if len(col) else pd.Series([None] * len(take))
    vals = vals.where(pd.Series(has), None) if not pd.api.types.is_numeric_dtype(col) else vals.where(pd.Series(has))
    name = f + suffix if f in conflict else f
    if pd.api.types.is_datetime64_any_dtype(col):
        out[name] = pd.to_datetime(vals.to_numpy(), utc=True) if getattr(col.dt, "tz", None) is None else vals.to_numpy()
    elif pd.api.types.is_integer_dtype(col):
        out[name] = pd.array(vals.to_numpy(dtype=float), dtype="Float64").astype("Int64")
    elif pd.api.types.is_float_dtype(col):
        out[name] = vals.to_numpy(dtype=float)
    else:
        out[name] = vals.astype(object).where(pd.Series(has), None).to_numpy()
md = np.where(has, rtime, np.datetime64("NaT", "ns"))
out["As Of Date"] = pd.to_datetime(md).tz_localize("UTC")
gap = (ltime - md) / np.timedelta64(1, "D")
out["Days From As Of Date"] = np.where(has, gap, np.nan).astype("float64")
out["As Of Status"] = status

summ = out["As Of Status"].value_counts().rename_axis("As Of Status").reset_index(name="Rows")
summ["Rows"] = summ["Rows"].astype("int64")
summ["Share"] = (summ["Rows"] / max(len(out), 1)).astype("float64")
gaps = out.loc[out["As Of Status"] == "Matched", "Days From As Of Date"]
summ["Average Days From As Of Date"] = np.where(summ["As Of Status"] == "Matched", float(gaps.mean()) if len(gaps) else np.nan, np.nan)
summ["Largest Days From As Of Date"] = np.where(summ["As Of Status"] == "Matched", float(gaps.abs().max()) if len(gaps) else np.nan, np.nan)

omniscope_api.write_output(out, "joined")
omniscope_api.write_output(summ, "summary")
n_match = int((status == "Matched").sum())
omniscope_api.close(f"{n_match:,} of {len(out):,} rows matched ({direction.lower()})" + (f"; {len(out) - n_match:,} without a record in force" if len(out) - n_match else "")
                    + (f"; {r_bad:,} input 2 rows without a valid date ignored" if r_bad else "") + ".")
