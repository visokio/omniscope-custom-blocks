"""Price Index: build your own price index (Laspeyres, Paasche and Fisher)
from prices and quantities per item and period: a cost index for what you buy,
a price index for what you sell, or a basket index for a category.

  Laspeyres  sum(p_t q_0) / sum(p_0 q_0)   (base-period quantities)
  Paasche    sum(p_t q_t) / sum(p_0 q_t)   (current-period quantities)
  Fisher     the geometric mean of the two
  plus a value index (sum p_t q_t / sum p_0 q_0) and the implied volume index.

Indices are 100 in the base period; items must have a price in the base
period and in the period compared. Optionally one index per group.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


item_f, per_f, p_f, q_f = opt("item_field"), opt("period_field"), opt("price_field"), opt("quantity_field")
group_f = opt("group_field")
base = opt("base_period", "")

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the prices and quantities to the input.")
for f, lab in ((item_f, "item"), (per_f, "period"), (p_f, "price"), (q_f, "quantity")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
if group_f and group_f not in df.columns:
    omniscope_api.abort(f"Field '{group_f}' is not in the input.")


def lab(v):
    if v is None or (isinstance(v, float) and v != v):
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    return str(v)


w = pd.DataFrame({"i": df[item_f].map(lab), "t": df[per_f].map(lab), "p": pd.to_numeric(df[p_f], errors="coerce").astype("float64"),
                  "q": pd.to_numeric(df[q_f], errors="coerce").astype("float64"), "g": df[group_f].map(lab).fillna("(blank)") if group_f else "All"}).dropna()
w = w.groupby(["g", "i", "t"], as_index=False).agg(p=("p", "mean"), q=("q", "sum"))
periods = sorted(w["t"].unique())
if not periods:
    omniscope_api.abort("No rows with an item, period, price and quantity.")
base = base or periods[0]
if base not in periods:
    omniscope_api.abort(f"Base period '{base}' is not in the data; periods are: {', '.join(periods[:10])}")
rows = []
for g, d in w.groupby("g", sort=True):
    b = d[d["t"] == base].set_index("i")
    for t in periods:
        c = d[d["t"] == t].set_index("i")
        common = b.index.intersection(c.index)
        if len(common) == 0:
            continue
        p0, q0, pt, qt = b.loc[common, "p"], b.loc[common, "q"], c.loc[common, "p"], c.loc[common, "q"]
        lasp = (pt * q0).sum() / (p0 * q0).sum() if (p0 * q0).sum() else np.nan
        paas = (pt * qt).sum() / (p0 * qt).sum() if (p0 * qt).sum() else np.nan
        fish = np.sqrt(lasp * paas) if lasp == lasp and paas == paas and lasp * paas > 0 else np.nan
        val = (pt * qt).sum() / (p0 * q0).sum() if (p0 * q0).sum() else np.nan
        rows.append({"Group": g, "Period": t, "Items Compared": int(len(common)), "Items Missing": int(len(b.index.union(c.index)) - len(common)),
                     "Laspeyres": 100 * lasp, "Paasche": 100 * paas, "Fisher": 100 * fish, "Value Index": 100 * val,
                     "Implied Volume Index": 100 * val / fish if fish == fish and fish else np.nan})
out = pd.DataFrame(rows)
for c in ("Items Compared", "Items Missing"):
    out[c] = out[c].astype("int64")
for c in ("Laspeyres", "Paasche", "Fisher", "Value Index", "Implied Volume Index"):
    out[c] = out[c].astype("float64")
if len(out):
    out["Fisher Change From Previous"] = (out.groupby("Group")["Fisher"].pct_change()).astype("float64")
if group_f:
    out = out.rename(columns={"Group": str(group_f)})
else:
    out = out.drop(columns=["Group"])
omniscope_api.write_output(out, "index")
last = out.iloc[-1] if len(out) else None
omniscope_api.close(f"{len(out):,} index points, base {base}" + (f"; latest Fisher {last['Fisher']:.1f} (Laspeyres {last['Laspeyres']:.1f}, Paasche {last['Paasche']:.1f})" if last is not None else "") + ".")
