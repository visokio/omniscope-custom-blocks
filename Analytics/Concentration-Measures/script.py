"""Concentration Measures: how concentrated a total is among the entities that
make it up (customers in revenue, suppliers in spend, firms in a market,
products in sales), overall and per group (market, region, year):

  Herfindahl-Hirschman index (HHI, sum of squared % shares, 0 to 10,000) and
  its normalised form, the equivalent number of equal-sized entities (1 / HHI),
  Gini coefficient, top-1 / top-4 (CR4) / top-10 shares, the share held by the
  top 20% of entities, the number of entities making up 50% and 80% of the
  total, and an HHI band with thresholds you can set (defaults 1,500 and
  2,500, the bands used in the 2010 US Horizontal Merger Guidelines).

Also the Lorenz curve (101 points per group) and each entity's share and rank.
Entities are summed first; zero and negative totals are left out.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


ent_f = opt("entity_field")
val_f = opt("value_field")
group_fields = list(opt("group_fields", []) or [])
lo_t = float(opt("hhi_moderate", 1500))
hi_t = float(opt("hhi_high", 2500))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
for f, lab in ((ent_f, "entity"), (val_f, "value")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
miss = [g for g in group_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Group fields not in the input: {', '.join(miss)}")
if not 0 < lo_t < hi_t <= 10000:
    omniscope_api.abort("HHI thresholds must satisfy 0 < moderate < high <= 10,000.")

w = pd.DataFrame({"e": df[ent_f].astype(object).where(df[ent_f].notna(), "(blank)").map(str),
                  "v": pd.to_numeric(df[val_f], errors="coerce").astype("float64")})
for g in group_fields:
    w[g] = df[g].astype(object).where(df[g].notna(), "(blank)").map(str)
if df[val_f].notna().any() and w["v"].isna().all():
    omniscope_api.abort(f"The value field '{val_f}' must be numeric.")
agg = w.groupby(group_fields + ["e"], sort=True)["v"].sum().reset_index()
dropped = int((agg["v"] <= 0).sum())
agg = agg[agg["v"] > 0]

srows, lrows, erows = [], [], []
groups = [((), agg)] if not group_fields else [((k if isinstance(k, tuple) else (k,)), g) for k, g in agg.groupby(group_fields, sort=True)]
for key, g in groups:
    gd = dict(zip(group_fields, key))
    v = np.sort(g["v"].to_numpy())[::-1]
    n = len(v)
    if n == 0:
        continue
    tot = v.sum()
    s = v / tot
    hhi = float(((100 * s) ** 2).sum())
    hhi_norm = (hhi / 10000 - 1 / n) / (1 - 1 / n) if n > 1 else 1.0
    asc = s[::-1]
    cum = np.cumsum(asc)
    gini = float(1 - 2 * (cum.sum() - cum[-1] / 2) / n) if n > 1 else 0.0  # trapezium rule under the Lorenz curve
    cs = np.cumsum(s)
    top20 = max(1, int(np.ceil(0.2 * n)))
    band = "Unconcentrated" if hhi < lo_t else "Moderately concentrated" if hhi <= hi_t else "Highly concentrated"
    srows.append({**gd, "Entities": n, "Total": float(tot), "HHI": hhi, "Normalised HHI": float(hhi_norm), "Equivalent Equal Entities": 10000 / hhi,
                  "Gini": gini, "Top 1 Share": float(s[0]), "Top 4 Share (CR4)": float(s[:4].sum()), "Top 10 Share": float(s[:10].sum()),
                  "Top 20% Of Entities Share": float(s[:top20].sum()), "Entities For 50%": int(np.searchsorted(cs, 0.5 - 1e-12) + 1),
                  "Entities For 80%": int(np.searchsorted(cs, 0.8 - 1e-12) + 1), "HHI Band": band, "Largest Entity": g.sort_values("v", ascending=False)["e"].iloc[0]})
    pts = np.linspace(0, 1, 101)
    xs = np.concatenate([[0.0], np.arange(1, n + 1) / n])
    ys = np.concatenate([[0.0], cum])
    for p_, yv in zip(pts, np.interp(pts, xs, ys)):
        lrows.append({**gd, "Share Of Entities": float(p_), "Share Of Total": float(yv), "Equality Line": float(p_)})
    order = g.sort_values(["v", "e"], ascending=[False, True])
    for r, (e, val) in enumerate(zip(order["e"], order["v"]), start=1):
        erows.append({**gd, str(ent_f): e, "Value": float(val), "Share": float(val / tot), "Rank": r, "Cumulative Share": float(cs[r - 1]),
                      "In Top 20%": "Yes" if r <= top20 else "No"})

scols = group_fields + ["Entities", "Total", "HHI", "Normalised HHI", "Equivalent Equal Entities", "Gini", "Top 1 Share", "Top 4 Share (CR4)", "Top 10 Share",
                        "Top 20% Of Entities Share", "Entities For 50%", "Entities For 80%", "HHI Band", "Largest Entity"]
summ = pd.DataFrame(srows, columns=scols)
for c in ("Entities", "Entities For 50%", "Entities For 80%"):
    summ[c] = summ[c].astype("int64")
for c in ("Total", "HHI", "Normalised HHI", "Equivalent Equal Entities", "Gini", "Top 1 Share", "Top 4 Share (CR4)", "Top 10 Share", "Top 20% Of Entities Share"):
    summ[c] = summ[c].astype("float64")
lor = pd.DataFrame(lrows, columns=group_fields + ["Share Of Entities", "Share Of Total", "Equality Line"])
for c in ("Share Of Entities", "Share Of Total", "Equality Line"):
    lor[c] = lor[c].astype("float64")
ents = pd.DataFrame(erows, columns=group_fields + [str(ent_f), "Value", "Share", "Rank", "Cumulative Share", "In Top 20%"])
ents["Rank"] = ents["Rank"].astype("int64")
for c in ("Value", "Share", "Cumulative Share"):
    ents[c] = ents[c].astype("float64")

omniscope_api.write_output(summ, "summary")
omniscope_api.write_output(lor, "lorenz")
omniscope_api.write_output(ents, "entities")
msg = f"{len(summ):,} group(s), {len(ents):,} entities"
if len(summ) == 1:
    r = summ.iloc[0]
    msg += f": HHI {r['HHI']:,.0f} ({r['HHI Band'].lower()}), Gini {r['Gini']:.2f}, top 20% hold {r['Top 20% Of Entities Share']:.0%}"
omniscope_api.close(msg + (f"; {dropped:,} entities with zero or negative totals left out" if dropped else "") + ".")
