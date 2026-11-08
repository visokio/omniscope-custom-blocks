"""Tile: assign each record to a tile (band) of a numeric field.

Methods:
  EQUAL_RECORDS  quantiles: deciles, quartiles... same number of records per tile
  EQUAL_SUM      each tile holds the same share of the field's total (Pareto bands)
  EQUAL_WIDTH    tiles of equal value range between the minimum and maximum
  SMART          bands by standard deviations from the mean
  MANUAL         your own cut points
Optionally within groups. Second output: one row per (group,) tile.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


value_field = opt("value_field")
method = opt("method", "EQUAL_RECORDS")
n_tiles = int(opt("tiles", 4))
group_fields = opt("group_fields", []) or []
cut_points = opt("cut_points", "")
highest_first = opt("highest_first", False)
prefix = opt("field_prefix", "Tile")

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
if not value_field or value_field not in df.columns:
    omniscope_api.abort(f"Choose a numeric value field that is in the input (got '{value_field}').")
miss = [g for g in group_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Group fields not in the input: {', '.join(miss)}")
values = pd.to_numeric(df[value_field], errors="coerce").astype("float64")
if values.notna().sum() == 0 and len(df):
    omniscope_api.abort(f"'{value_field}' has no numeric values.")
cuts = []
if method == "MANUAL":
    try:
        cuts = sorted(float(c) for c in re.split(r"[,;\s]+", cut_points.strip()) if c)
    except ValueError:
        omniscope_api.abort("Cut points must be numbers separated by commas, such as 100, 500, 1000.")
    if not cuts:
        omniscope_api.abort("Enter at least one cut point for the manual method.")
    n_tiles = len(cuts) + 1
if method == "SMART":
    n_tiles = 6
if n_tiles < 1:
    omniscope_api.abort("Number of tiles must be at least 1.")

SMART_LABELS = {1: "Extremely low", 2: "Low", 3: "Below average", 4: "Above average", 5: "High", 6: "Extremely high"}


def fmt(v):
    if v is None or not np.isfinite(v):
        return ""
    return f"{v:,.0f}" if abs(v) >= 100 or float(v).is_integer() else f"{v:,.4g}"


def tile_group(v):
    """Return (tile numbers 1..n as float with NaN, label array) for one group's values."""
    t = pd.Series(np.nan, index=v.index)
    lab = pd.Series(None, index=v.index, dtype=object)
    ok = v.notna()
    x = v[ok]
    if x.empty:
        return t, lab
    if method == "EQUAL_RECORDS":
        r = x.rank(method="first")
        t[ok] = np.ceil(r / len(x) * n_tiles).clip(1, n_tiles)
    elif method == "EQUAL_SUM":
        order = x.sort_values(kind="mergesort")
        total = order.clip(lower=0).sum()
        if total <= 0:
            share = pd.Series(np.arange(1, len(order) + 1) / len(order), index=order.index)
        else:
            share = order.clip(lower=0).cumsum() / total
        # a record belongs to the tile its cumulative share ends in
        t[order.index] = np.ceil(share * n_tiles - 1e-9).clip(1, n_tiles)
    elif method == "EQUAL_WIDTH":
        lo, hi = x.min(), x.max()
        if hi == lo:
            t[ok] = 1
        else:
            t[ok] = np.floor((x - lo) / (hi - lo) * n_tiles).clip(0, n_tiles - 1) + 1
    elif method == "SMART":
        mu, sd = x.mean(), x.std(ddof=0)
        z = (x - mu) / sd if sd > 0 else x * 0
        bands = np.select([z < -2, z < -1, z < 0, z < 1, z < 2], [1, 2, 3, 4, 5], 6)
        t[ok] = bands
        lab[ok] = [SMART_LABELS[b] for b in bands]
    elif method == "MANUAL":
        t[ok] = np.searchsorted(np.array(cuts), x.to_numpy(), side="right") + 1
    if highest_first and method != "SMART":
        top = n_tiles
        t[ok] = top + 1 - t[ok]
    # range labels from the data actually in each tile
    if method != "SMART":
        for k, sub in x.groupby(t[ok]):
            lab[sub.index] = f"{fmt(sub.min())} to {fmt(sub.max())}"
    return t, lab


if group_fields:
    keys = [df[c].astype(object).where(df[c].notna(), "\u0000null") for c in group_fields]
    groups = {k: values.index[v] for k, v in values.groupby(keys, sort=False).indices.items()}
else:
    groups = {None: values.index}

tile = pd.Series(np.nan, index=df.index)
label = pd.Series(None, index=df.index, dtype=object)
for _, idx in groups.items():
    t, lab = tile_group(values.loc[idx])
    tile.loc[idx] = t
    label.loc[idx] = lab

out = df.copy()
out[f"{prefix} Number"] = pd.array(tile.to_numpy(), dtype="Float64").astype("Int64")
out[f"{prefix} Range" if method != "SMART" else f"{prefix} Label"] = label.where(label.notna(), None)

summ = pd.DataFrame({"__t": out[f"{prefix} Number"], "__v": values})
for g in group_fields:
    summ[g] = df[g]
summ = summ.dropna(subset=["__t"])
agg = summ.groupby(group_fields + ["__t"], dropna=False).agg(Records=("__v", "size"), Minimum=("__v", "min"),
                                                            Maximum=("__v", "max"), Total=("__v", "sum")).reset_index()
grand = agg.groupby(group_fields)["Total"].transform("sum") if group_fields else agg["Total"].sum()
agg["Share Of Total"] = np.where(np.asarray(grand) == 0, np.nan, agg["Total"] / grand)
agg["Share Of Records"] = agg["Records"] / (agg.groupby(group_fields)["Records"].transform("sum") if group_fields else agg["Records"].sum())
agg = agg.rename(columns={"__t": f"{prefix} Number"})
agg[f"{prefix} Number"] = agg[f"{prefix} Number"].astype("Int64")
agg["Records"] = agg["Records"].astype("int64")
for c in ("Minimum", "Maximum", "Total", "Share Of Total", "Share Of Records"):
    agg[c] = agg[c].astype("float64")
if agg.empty:
    agg = pd.DataFrame({**{g: pd.Series(dtype=object) for g in group_fields}, f"{prefix} Number": pd.Series(dtype="Int64"),
                        "Records": pd.Series(dtype="int64"), "Minimum": pd.Series(dtype="float64"),
                        "Maximum": pd.Series(dtype="float64"), "Total": pd.Series(dtype="float64"),
                        "Share Of Total": pd.Series(dtype="float64"), "Share Of Records": pd.Series(dtype="float64")})

omniscope_api.write_output(out, "tiled")
omniscope_api.write_output(agg, "summary")
omniscope_api.close(f"{int(tile.notna().sum()):,} records tiled into {n_tiles} tiles ({method.replace('_', ' ').lower()})"
                    + (f" within {len(groups):,} groups" if group_fields else "") + ".")
