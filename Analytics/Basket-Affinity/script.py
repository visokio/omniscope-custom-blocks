"""Basket Affinity Matrix: from transaction lines (basket / order ID + item),
measure how often every pair of items is bought together: co-occurrence count,
support, confidence in both directions, lift and Jaccard similarity; plus a
per-item summary with its strongest partners. A compact, all-pairs view that
complements rule mining (native Basket Analysis).
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


basket_f = opt("basket_field")
item_f = opt("item_field")
max_items = int(opt("max_items", 50))
min_baskets = int(opt("min_item_baskets", 5))
min_pair = int(opt("min_pair_baskets", 3))
partners = int(opt("top_partners", 3))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the transaction lines to the input.")
for f, label in ((basket_f, "basket"), (item_f, "item")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
if basket_f == item_f:
    omniscope_api.abort("Basket and item fields must differ.")

t = pd.DataFrame({"b": df[basket_f].astype(object), "i": df[item_f].astype(object)}).dropna().drop_duplicates()
t["i"] = t["i"].astype(str)
n_baskets = t["b"].nunique()
item_counts = t.groupby("i")["b"].nunique().sort_values(ascending=False)
kept = item_counts[item_counts >= min_baskets].head(max_items)
items = kept.index.tolist()
t = t[t["i"].isin(items)]

pair_rows, item_rows = [], []
if len(items) >= 2 and n_baskets:
    bcodes, buniq = pd.factorize(t["b"])
    icodes = pd.Index(items).get_indexer(t["i"])
    X = np.zeros((len(buniq), len(items)), dtype=np.float32)  # float so the product uses BLAS (integer matmul is slow)
    X[bcodes, icodes] = 1.0
    C = np.rint(X.T @ X).astype(np.int64)  # co-occurrence; diagonal = baskets containing the item
    cnt = np.diag(C).astype(float)
    sup = cnt / n_baskets
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            both = int(C[a, b])
            if both < min_pair:
                continue
            s_ab = both / n_baskets
            lift = s_ab / (sup[a] * sup[b])
            pair_rows.append({"Item A": items[a], "Item B": items[b], "Baskets With Both": both, "Support": s_ab,
                              "Confidence A to B": both / cnt[a], "Confidence B to A": both / cnt[b], "Lift": lift,
                              "Jaccard": both / (cnt[a] + cnt[b] - both)})
pairs = pd.DataFrame(pair_rows, columns=["Item A", "Item B", "Baskets With Both", "Support", "Confidence A to B", "Confidence B to A", "Lift", "Jaccard"])
pairs = pairs.sort_values(["Lift", "Baskets With Both"], ascending=False).reset_index(drop=True)
pairs["Baskets With Both"] = pairs["Baskets With Both"].astype("int64")
for c in ("Support", "Confidence A to B", "Confidence B to A", "Lift", "Jaccard"):
    pairs[c] = pairs[c].astype("float64")
pairs["Association"] = np.where(pairs["Lift"] >= 1.5, "Strong positive", np.where(pairs["Lift"] > 1.1, "Positive",
                       np.where(pairs["Lift"] < 0.9, "Negative (bought apart)", "Independent")))

both_dirs = pd.concat([pairs.rename(columns={"Item A": "Item", "Item B": "Partner"}),
                       pairs.rename(columns={"Item B": "Item", "Item A": "Partner"})], ignore_index=True)
top_by_item = {}
for it, p in both_dirs[both_dirs["Lift"] > 1].sort_values("Lift", ascending=False).groupby("Item", sort=False):
    top_by_item[it] = ", ".join(f"{r.Partner} ({r.Lift:.1f}x)" for r in p.head(partners).itertuples())
n_pairs = both_dirs.groupby("Item").size().to_dict()
for it in items:
    item_rows.append({"Item": it, "Baskets": int(item_counts[it]), "Support": float(item_counts[it] / n_baskets) if n_baskets else np.nan,
                      "Top Partners (by lift)": top_by_item.get(it, ""), "Pairs Found": int(n_pairs.get(it, 0))})
summ = pd.DataFrame(item_rows, columns=["Item", "Baskets", "Support", "Top Partners (by lift)", "Pairs Found"])
summ["Baskets"] = summ["Baskets"].astype("int64")
summ["Pairs Found"] = summ["Pairs Found"].astype("int64")
summ["Support"] = summ["Support"].astype("float64")

omniscope_api.write_output(pairs, "pairs")
omniscope_api.write_output(summ, "items")
dropped = int((item_counts < min_baskets).sum()) + max(0, int((item_counts >= min_baskets).sum()) - max_items)
omniscope_api.close(f"{n_baskets:,} baskets, {len(items)} items analysed, {len(pairs):,} pairs"
                    + (f"; {dropped:,} rarer items left out." if dropped else "."))
