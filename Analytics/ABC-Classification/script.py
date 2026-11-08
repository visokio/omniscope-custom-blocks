"""ABC Classification (with optional XYZ): rank items by value and classify
them by cumulative share (A = the top 80% of value, B = the next 15%, C = the
rest), optionally within groups; with a date field, also classify demand
variability per item (X = steady, Y = variable, Z = erratic, by coefficient of
variation across periods) for the ABC-XYZ matrix used in inventory planning.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


item_field = opt("item_field")
value_field = opt("value_field")
group_fields = opt("group_fields", []) or []
a_share = float(opt("a_share", 0.8))
b_share = float(opt("b_share", 0.95))
date_field = opt("date_field")
xyz_field = opt("xyz_field")
period = opt("period", "MONTH")
x_cv = float(opt("x_cv", 0.5))
y_cv = float(opt("y_cv", 1.0))
FREQ = {"WEEK": "W-SUN", "MONTH": "M", "QUARTER": "Q-DEC"}

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the items or sales lines to the input.")
for f, label in ((item_field, "item"), (value_field, "value")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
for f in list(group_fields) + [date_field, xyz_field]:
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")
if not 0 < a_share < b_share < 1:
    omniscope_api.abort("Class thresholds must satisfy 0 < A < B < 1, for example 0.8 and 0.95.")
if not 0 < x_cv < y_cv:
    omniscope_api.abort("XYZ thresholds must satisfy 0 < X < Y, for example 0.5 and 1.0.")

keys = list(group_fields) + [item_field]
work = df[keys].copy()
work["__v"] = pd.to_numeric(df[value_field], errors="coerce").fillna(0.0).astype("float64")
for k in keys:
    work[k] = work[k].astype(object).where(work[k].notna(), "(blank)")
items = work.groupby(keys, sort=False, dropna=False)["__v"].sum().reset_index().rename(columns={"__v": "Total Value"})

gk = list(group_fields)
items = items.sort_values(gk + ["Total Value", item_field], ascending=[True] * len(gk) + [False, True], kind="mergesort").reset_index(drop=True)
if gk:
    grp = items.groupby(gk, sort=False)
    tot = grp["Total Value"].transform(lambda s: s.clip(lower=0).sum())
    cum = grp["Total Value"].transform(lambda s: s.clip(lower=0).cumsum())
    rank = grp.cumcount() + 1
    cnt = grp["Total Value"].transform("size")
else:
    tot = pd.Series(items["Total Value"].clip(lower=0).sum(), index=items.index)
    cum = items["Total Value"].clip(lower=0).cumsum()
    rank = pd.Series(np.arange(1, len(items) + 1), index=items.index)
    cnt = pd.Series(len(items), index=items.index)
share = (items["Total Value"].clip(lower=0) / tot.where(tot > 0)).fillna(0.0)
cum_share = (cum / tot.where(tot > 0)).fillna(0.0)
prev_cum = cum_share - share
# an item belongs to the class in which its cumulative share starts (so the item crossing 80% is still A)
items["Value Share"] = share.astype("float64")
items["Cumulative Share"] = cum_share.astype("float64")
items["Rank"] = pd.array(rank.to_numpy(), dtype="Int64")
items["Rank Percentile"] = (rank / cnt).astype("float64")
items["ABC Class"] = np.where(prev_cum < a_share - 1e-12, "A", np.where(prev_cum < b_share - 1e-12, "B", "C"))
items.loc[items["Total Value"] <= 0, "ABC Class"] = "C"

xyz = False
if date_field:
    xyz = True
    d = df[date_field]
    if pd.api.types.is_datetime64_any_dtype(d):
        dates = d.dt.tz_localize(None) if d.dt.tz is not None else d
    else:
        txt = d.astype(object).where(d.notna(), None).astype(str).str.strip()
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        dates = pd.Series(pd.NaT, index=d.index, dtype="datetime64[ns]")
        dates[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
        dates[~iso & d.notna()] = pd.to_datetime(txt[~iso & d.notna()], errors="coerce", dayfirst=True, format="mixed")
    q = pd.to_numeric(df[xyz_field], errors="coerce").fillna(0.0) if xyz_field else work["__v"]
    per = dates.dt.to_period(FREQ.get(period, "M"))
    t = work[keys].copy()
    t["__p"] = per
    t["__q"] = q.astype("float64").to_numpy()
    t = t[t["__p"].notna()]
    all_periods = pd.period_range(t["__p"].min(), t["__p"].max(), freq=FREQ.get(period, "M")) if len(t) else []
    pt = t.groupby(keys + ["__p"], dropna=False)["__q"].sum().unstack("__p").reindex(columns=all_periods).fillna(0.0)
    mean = pt.mean(axis=1)
    sd = pt.std(axis=1, ddof=0)
    cv = (sd / mean.where(mean > 0)).rename("Coefficient Of Variation")
    stats = pd.DataFrame({"Periods": len(all_periods), "Average Per Period": mean, "Coefficient Of Variation": cv}).reset_index()
    items = items.merge(stats, on=keys, how="left")
    c = items["Coefficient Of Variation"]
    items["XYZ Class"] = np.where(c.isna(), "Z", np.where(c <= x_cv, "X", np.where(c <= y_cv, "Y", "Z")))
    items["ABC-XYZ"] = items["ABC Class"] + items["XYZ Class"]
    items["Periods"] = pd.array(items["Periods"].fillna(0).to_numpy(), dtype="Float64").astype("Int64")

ADVICE = {"A": "Tight control: review often, forecast carefully, high service level.",
          "B": "Moderate control: periodic review.",
          "C": "Simple rules: bulk ordering, low review effort."}
summ = items.groupby(gk + ["ABC Class"], dropna=False).agg(Items=(item_field, "size"), Value=("Total Value", "sum")).reset_index()
if gk:
    summ["Share Of Items"] = summ["Items"] / summ.groupby(gk)["Items"].transform("sum")
    summ["Share Of Value"] = summ["Value"] / summ.groupby(gk)["Value"].transform("sum")
else:
    summ["Share Of Items"] = summ["Items"] / max(1, summ["Items"].sum())
    summ["Share Of Value"] = summ["Value"] / summ["Value"].sum() if summ["Value"].sum() else np.nan
summ["Suggested Policy"] = summ["ABC Class"].map(ADVICE)
summ["Items"] = summ["Items"].astype("int64")
for cc in ("Value", "Share Of Items", "Share Of Value"):
    summ[cc] = summ[cc].astype("float64")
if summ.empty:
    summ = pd.DataFrame({**{g: pd.Series([], dtype=object) for g in gk}, "ABC Class": pd.Series([], dtype=object),
                         "Items": pd.Series([], dtype="int64"), "Value": pd.Series([], dtype="float64"),
                         "Share Of Items": pd.Series([], dtype="float64"), "Share Of Value": pd.Series([], dtype="float64"),
                         "Suggested Policy": pd.Series([], dtype=object)})

omniscope_api.write_output(items, "items")
omniscope_api.write_output(summ, "classes")
nA = int((items["ABC Class"] == "A").sum())
omniscope_api.close(f"{len(items):,} items classified: {nA:,} A, {int((items['ABC Class'] == 'B').sum()):,} B, "
                    f"{int((items['ABC Class'] == 'C').sum()):,} C" + (" (with XYZ)." if xyz else "."))
