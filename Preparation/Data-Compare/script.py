"""Data Compare: compare two versions of a dataset (before / after, source /
target, last month / this month) and report

  per record: Added, Removed, Changed or Unchanged, with the fields that changed,
  per difference: one row per changed value, old and new, and the numeric change,
  per field: how many values changed, and fields that exist on one side only.

Records are matched on key fields; without keys, whole rows are matched (each
duplicate counted). Options: numeric tolerance, ignore case, trim spaces, and
whether blank text equals null. Duplicate keys are reported, not guessed at.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


keys = list(opt("key_fields", []) or [])
compare = list(opt("compare_fields", []) or [])
ignore = list(opt("ignore_fields", []) or [])
tol = float(opt("tolerance", 0.0) or 0.0)
rel_tol = float(opt("relative_tolerance", 0.0) or 0.0)
icase = bool(opt("ignore_case", False))
trim = bool(opt("trim", True))
blank_null = bool(opt("blank_is_null", True))
show_unchanged = bool(opt("include_unchanged", True))

old = omniscope_api.read_input_records(input_number=0)
new = omniscope_api.read_input_records(input_number=1)
if old is None or new is None:
    omniscope_api.abort("Connect the old (before) data to input 1 and the new (after) data to input 2.")
miss = [k for k in keys if k not in old.columns or k not in new.columns]
if miss:
    omniscope_api.abort(f"Key fields must be in both inputs: {', '.join(miss)}")
common = [c for c in old.columns if c in new.columns]
only_old = [c for c in old.columns if c not in new.columns]
only_new = [c for c in new.columns if c not in old.columns]
if compare:
    bad = [c for c in compare if c not in common]
    if bad:
        omniscope_api.abort(f"Fields to compare must be in both inputs: {', '.join(bad)}")
    fields = [c for c in compare if c not in keys]
else:
    fields = [c for c in common if c not in keys and c not in ignore]


def show_text(s):
    """Values as text for display: whole floats without .0, dates as ISO, None for nulls."""
    t = s.astype(object).where(s.notna(), None)
    return t.map(lambda v: v if v is None else (str(int(v)) if isinstance(v, float) and v.is_integer() else
                                                f"{v:.12g}" if isinstance(v, float) else
                                                v.isoformat() if isinstance(v, pd.Timestamp) else str(v)))


def norm_text(s):
    t = show_text(s)
    if trim:
        t = t.map(lambda v: v if v is None else v.strip())
    if icase:
        t = t.map(lambda v: v if v is None else v.lower())
    if blank_null:
        t = t.map(lambda v: None if v == "" else v)
    return t


def key_frame(df):
    k = pd.DataFrame({c: norm_text(df[c]) for c in keys}, index=df.index)
    return k.fillna("\u0000null")


def is_num(s):
    return pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)


def is_dt(s):
    return pd.api.types.is_datetime64_any_dtype(s)


def type_name(s):
    """Omniscope's name for a field type, the same whichever pandas version runs the block."""
    if pd.api.types.is_bool_dtype(s):
        return "Boolean"
    if pd.api.types.is_integer_dtype(s):
        return "Integer number"
    if is_num(s):
        return "Decimal number"
    if is_dt(s):
        return "Date"
    return "Text"


# ---- match records
o = old.reset_index(drop=True)
n = new.reset_index(drop=True)
if keys:
    ko, kn = key_frame(o), key_frame(n)
    ko["__k"] = ko[keys].agg("\u0001".join, axis=1) if len(ko) else pd.Series(dtype=object)
    kn["__k"] = kn[keys].agg("\u0001".join, axis=1) if len(kn) else pd.Series(dtype=object)
else:
    allf = [c for c in common if c not in ignore]
    if not allf:
        omniscope_api.abort("The inputs have no fields in common to compare.")
    ko = pd.DataFrame({c: norm_text(o[c]) for c in allf}).fillna("\u0000null")
    kn = pd.DataFrame({c: norm_text(n[c]) for c in allf}).fillna("\u0000null")
    ko["__k"] = ko.agg("\u0001".join, axis=1) if len(ko) else pd.Series(dtype=object)
    kn["__k"] = kn.agg("\u0001".join, axis=1) if len(kn) else pd.Series(dtype=object)
    ko["__k"] = ko["__k"] + "\u0002" + ko.groupby("__k").cumcount().astype(str)
    kn["__k"] = kn["__k"] + "\u0002" + kn.groupby("__k").cumcount().astype(str)
    fields = []
dup_o = set(ko["__k"][ko["__k"].duplicated(keep=False)])
dup_n = set(kn["__k"][kn["__k"].duplicated(keep=False)])
dups = dup_o | dup_n
lo = pd.DataFrame({"__k": ko["__k"], "__io": np.arange(len(o))})
ln = pd.DataFrame({"__k": kn["__k"], "__in": np.arange(len(n))})
lo = lo[~lo["__k"].isin(dups)]
ln = ln[~ln["__k"].isin(dups)]
m = lo.merge(ln, on="__k", how="outer")
both = m["__io"].notna() & m["__in"].notna()
mb = m[both]
io, inn = mb["__io"].astype(int).to_numpy(), mb["__in"].astype(int).to_numpy()

# ---- compare values on matched records
changed = np.zeros((len(mb), len(fields)), dtype=bool)
diff_parts = []
for j, f in enumerate(fields):
    a, b = o[f].iloc[io].reset_index(drop=True), n[f].iloc[inn].reset_index(drop=True)
    numeric = is_num(a) and is_num(b)
    if numeric:
        av, bv = a.astype("float64").to_numpy(), b.astype("float64").to_numpy()
        both_na = np.isnan(av) & np.isnan(bv)
        one_na = np.isnan(av) ^ np.isnan(bv)
        lim = np.maximum(tol, rel_tol * np.abs(av))
        with np.errstate(invalid="ignore"):
            ne = one_na | (~both_na & ~one_na & (np.abs(bv - av) > lim + 1e-12))
        delta = np.where(ne & ~one_na, bv - av, np.nan)
    elif is_dt(a) and is_dt(b):
        at = pd.to_datetime(a, utc=True)
        bt = pd.to_datetime(b, utc=True)
        ne = ((at != bt) & ~(at.isna() & bt.isna())).to_numpy()
        delta = np.where(ne, ((bt - at).dt.total_seconds() / 86400).to_numpy(dtype=float), np.nan)
    else:
        at, bt = norm_text(a), norm_text(b)
        ne = ~((at == bt) | (at.isna() & bt.isna())).to_numpy(dtype=bool)
        av = pd.to_numeric(a, errors="coerce").to_numpy(dtype=float) if not is_dt(a) else np.full(len(a), np.nan)
        bv = pd.to_numeric(b, errors="coerce").to_numpy(dtype=float) if not is_dt(b) else np.full(len(b), np.nan)
        if numeric is False and tol > 0:
            okn = ~np.isnan(av) & ~np.isnan(bv)
            ne = np.where(okn, np.abs(bv - av) > np.maximum(tol, rel_tol * np.abs(av)) + 1e-12, ne)
        delta = np.where(ne, bv - av, np.nan)
    changed[:, j] = ne
    if ne.any():
        idx = np.nonzero(ne)[0]
        diff_parts.append(pd.DataFrame({"__io": io[idx], "__in": inn[idx], "Field": f,
                                        "Old Value": show_text(a.iloc[idx].astype("float64") if numeric else a.iloc[idx]).to_numpy(dtype=object),
                                        "New Value": show_text(b.iloc[idx].astype("float64") if numeric else b.iloc[idx]).to_numpy(dtype=object),
                                        "Change": delta[idx]}))

# ---- records output
key_out_cols = keys if keys else [c for c in common if c not in ignore]


def key_values(src, rows):
    return {c: src[c].iloc[rows].to_numpy(dtype=object) for c in key_out_cols}


recs = []
nch = changed.sum(axis=1)
names = np.array(fields, dtype=object)
chg_list = ["; ".join(names[changed[i]]) for i in range(len(mb))] if fields else [""] * len(mb)
r_both = pd.DataFrame(key_values(n, inn))
r_both["Status"] = np.where(nch > 0, "Changed", "Unchanged")
r_both["Fields Changed"] = nch.astype("int64")
r_both["Changed Fields"] = chg_list
r_both["Old Row"], r_both["New Row"] = io + 1, inn + 1
rem = m[m["__io"].notna() & m["__in"].isna()]["__io"].astype(int).to_numpy()
add = m[m["__io"].isna() & m["__in"].notna()]["__in"].astype(int).to_numpy()
r_rem = pd.DataFrame(key_values(o, rem))
r_rem["Status"], r_rem["Fields Changed"], r_rem["Changed Fields"], r_rem["Old Row"], r_rem["New Row"] = "Removed", 0, "", rem + 1, np.nan
r_add = pd.DataFrame(key_values(n, add))
r_add["Status"], r_add["Fields Changed"], r_add["Changed Fields"], r_add["Old Row"], r_add["New Row"] = "Added", 0, "", np.nan, add + 1
d_o = np.nonzero(ko["__k"].isin(dups).to_numpy())[0]
d_n = np.nonzero(kn["__k"].isin(dups).to_numpy())[0]
r_do = pd.DataFrame(key_values(o, d_o))
r_do["Status"], r_do["Fields Changed"], r_do["Changed Fields"], r_do["Old Row"], r_do["New Row"] = "Duplicate key (old)", 0, "", d_o + 1, np.nan
r_dn = pd.DataFrame(key_values(n, d_n))
r_dn["Status"], r_dn["Fields Changed"], r_dn["Changed Fields"], r_dn["Old Row"], r_dn["New Row"] = "Duplicate key (new)", 0, "", np.nan, d_n + 1
parts = [r_rem, r_add, r_both[r_both["Status"] == "Changed"], r_do, r_dn] + ([r_both[r_both["Status"] == "Unchanged"]] if show_unchanged else [])
records = pd.concat([p for p in parts if len(p)] or [r_both.iloc[0:0]], ignore_index=True)
ORDER = {"Changed": 0, "Added": 1, "Removed": 2, "Duplicate key (old)": 3, "Duplicate key (new)": 4, "Unchanged": 5}
records = records.sort_values(["Status", "Old Row", "New Row"], key=lambda s: s.map(ORDER) if s.name == "Status" else s, kind="mergesort").reset_index(drop=True)
records["Changed Fields"] = records["Changed Fields"].replace("", None)
records["Fields Changed"] = records["Fields Changed"].astype("int64")
records["Old Row"] = pd.array(records["Old Row"].to_numpy(dtype=float), dtype="Float64").astype("Int64")
records["New Row"] = pd.array(records["New Row"].to_numpy(dtype=float), dtype="Float64").astype("Int64")

# ---- differences output
if diff_parts:
    d = pd.concat(diff_parts, ignore_index=True)
    kv = pd.DataFrame(key_values(n, d["__in"].to_numpy()))
    diffs = pd.concat([kv, d[["Field", "Old Value", "New Value", "Change"]].reset_index(drop=True)], axis=1)
    forder = {f: i for i, f in enumerate(fields)}
    diffs["__o"] = d["__in"].to_numpy()
    diffs["__f"] = diffs["Field"].map(forder)
    diffs = diffs.sort_values(["__o", "__f"], kind="mergesort").drop(columns=["__o", "__f"]).reset_index(drop=True)
else:
    diffs = pd.DataFrame({**{c: pd.Series([], dtype=object) for c in key_out_cols}, "Field": pd.Series([], dtype=object),
                          "Old Value": pd.Series([], dtype=object), "New Value": pd.Series([], dtype=object), "Change": pd.Series([], dtype="float64")})
diffs["Change"] = diffs["Change"].astype("float64")

# ---- field summary
srows = []
for j, f in enumerate(fields):
    c = int(changed[:, j].sum())
    srows.append({"Field": f, "Status": "Compared", "Old Type": type_name(old[f]), "New Type": type_name(new[f]), "Records Compared": len(mb),
                  "Values Changed": c, "Share Changed": c / len(mb) if len(mb) else np.nan})
for f in keys:
    srows.append({"Field": f, "Status": "Key", "Old Type": type_name(old[f]), "New Type": type_name(new[f]), "Records Compared": len(mb), "Values Changed": 0, "Share Changed": np.nan})
for f in only_old:
    srows.append({"Field": f, "Status": "Only in old", "Old Type": type_name(old[f]), "New Type": None, "Records Compared": 0, "Values Changed": 0, "Share Changed": np.nan})
for f in only_new:
    srows.append({"Field": f, "Status": "Only in new", "Old Type": None, "New Type": type_name(new[f]), "Records Compared": 0, "Values Changed": 0, "Share Changed": np.nan})
for f in ignore:
    if f in common and f not in keys:
        srows.append({"Field": f, "Status": "Ignored", "Old Type": type_name(old[f]), "New Type": type_name(new[f]), "Records Compared": 0, "Values Changed": 0, "Share Changed": np.nan})
summ = pd.DataFrame(srows, columns=["Field", "Status", "Old Type", "New Type", "Records Compared", "Values Changed", "Share Changed"])
for c in ("Records Compared", "Values Changed"):
    summ[c] = summ[c].astype("int64")
summ["Share Changed"] = summ["Share Changed"].astype("float64")

omniscope_api.write_output(records, "records")
omniscope_api.write_output(diffs, "differences")
omniscope_api.write_output(summ, "fields")
cnt = records["Status"].value_counts()
parts_msg = [f"{int(cnt.get(s, 0)):,} {s.lower()}" for s in ("Changed", "Added", "Removed")]
if not show_unchanged:
    parts_msg.append(f"{int((r_both['Status'] == 'Unchanged').sum()):,} unchanged (not listed)")
else:
    parts_msg.append(f"{int(cnt.get('Unchanged', 0)):,} unchanged")
nd = len(d_o) + len(d_n)
omniscope_api.close(", ".join(parts_msg) + f"; {len(diffs):,} values differ" + (f"; {nd:,} rows with duplicate keys not compared" if nd else "")
                    + (f"; fields only in old: {', '.join(only_old[:5])}" if only_old else "") + (f"; only in new: {', '.join(only_new[:5])}" if only_new else "") + ".")
