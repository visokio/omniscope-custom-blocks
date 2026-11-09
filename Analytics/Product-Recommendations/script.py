"""Product Recommendations: "customers who bought X also bought Y", turned into
a ranked list of products each customer has not bought yet.

  Item-to-item collaborative filtering: products are similar when the same
  customers buy them (cosine similarity on who bought what, with optional
  shrinkage so that pairs seen with few customers count less). A customer's
  score for a product is the sum of its similarity to the products they bought.
  Each recommendation says which of their purchases it comes from most
  ("because you bought").

Outputs: top recommendations per customer, the most similar products per
product (for "you may also like" on a product page), and coverage figures.
Products bought by fewer customers than the minimum are left out.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


cust_f = opt("customer_field")
item_f = opt("product_field")
top_n = int(opt("top_n", 5))
top_sim = int(opt("similar_per_product", 10))
min_cust = int(opt("min_customers", 5))
shrink = float(opt("shrinkage", 10) or 0)
exclude_bought = bool(opt("exclude_bought", True))
max_items = 8000

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the purchases (customer, product) to the input.")
for f, lab in ((cust_f, "customer"), (item_f, "product")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
w = pd.DataFrame({"c": df[cust_f].astype(object), "i": df[item_f].astype(object)}).dropna()
w["c"], w["i"] = w["c"].map(str), w["i"].map(str)
w = w.drop_duplicates()
pop = w.groupby("i")["c"].nunique()
keep = pop[pop >= min_cust].index
if len(keep) > max_items:
    omniscope_api.abort(f"{len(keep):,} products are bought by at least {min_cust} customers; raise the minimum so at most {max_items:,} remain.")
w = w[w["i"].isin(keep)]
items = sorted(keep)
custs = sorted(w["c"].unique())
ii = {k: n for n, k in enumerate(items)}
ci = {k: n for n, k in enumerate(custs)}
X = np.zeros((len(custs), len(items)), dtype=np.float32)
if len(w):
    X[w["c"].map(ci).to_numpy(), w["i"].map(ii).to_numpy()] = 1.0
co = X.T @ X                         # customers buying both
cnt = np.diag(co).copy()
with np.errstate(divide="ignore", invalid="ignore"):
    S = co / np.sqrt(np.outer(cnt, cnt))
S = np.nan_to_num(S)
if shrink > 0:
    S = S * (co / (co + shrink))     # pairs seen with few customers count less
np.fill_diagonal(S, 0.0)
S = S.astype(np.float32)

# similar products
srows = []
for a in range(len(items)):
    if top_sim <= 0:
        break
    sims = S[a]
    k = min(top_sim, len(items) - 1)
    if k <= 0:
        continue
    idx = np.argpartition(-sims, k - 1)[:k]
    idx = idx[np.argsort(-sims[idx], kind="stable")]
    for r, b in enumerate(idx, start=1):
        if sims[b] <= 0:
            break
        srows.append({"Product": items[a], "Similar Product": items[b], "Similarity": float(sims[b]), "Customers Who Bought Both": int(co[a, b]),
                      "Customers Who Bought Product": int(cnt[a]), "Rank": r})
sim_df = pd.DataFrame(srows, columns=["Product", "Similar Product", "Similarity", "Customers Who Bought Both", "Customers Who Bought Product", "Rank"])

# recommendations, in chunks of customers
rrows = []
CH = 2000
for s0 in range(0, len(custs), CH):
    Xc = X[s0:s0 + CH]
    sc = Xc @ S
    if exclude_bought:
        sc[Xc > 0] = -np.inf
    k = min(top_n, len(items))
    if k <= 0:
        break
    part = np.argpartition(-sc, k - 1, axis=1)[:, :k]
    for row in range(Xc.shape[0]):
        cand = part[row][np.argsort(-sc[row, part[row]], kind="stable")]
        bought = np.nonzero(Xc[row])[0]
        r = 0
        for j in cand:
            if not np.isfinite(sc[row, j]) or sc[row, j] <= 0:
                break
            r += 1
            contrib = S[bought, j]
            best = bought[int(np.argmax(contrib))]
            rrows.append({str(cust_f): custs[s0 + row], "Rank": r, "Recommended Product": items[j], "Score": float(sc[row, j]),
                          "Because You Bought": items[best], "Similarity To That Product": float(contrib.max()),
                          "Products Bought": int(len(bought))})
rec = pd.DataFrame(rrows, columns=[str(cust_f), "Rank", "Recommended Product", "Score", "Because You Bought", "Similarity To That Product", "Products Bought"])
for c in ("Rank", "Products Bought"):
    rec[c] = rec[c].astype("int64")
for c in ("Score", "Similarity To That Product"):
    rec[c] = rec[c].astype("float64")
for c in ("Customers Who Bought Both", "Customers Who Bought Product", "Rank"):
    sim_df[c] = sim_df[c].astype("int64")
sim_df["Similarity"] = sim_df["Similarity"].astype("float64")
cov = pd.DataFrame([{"Customers": len(custs), "Customers With Recommendations": int(rec[str(cust_f)].nunique()) if len(rec) else 0,
                     # Products = Products Scored + Products Left Out: every distinct product in the purchases
                     "Products": int(len(pop)), "Products Scored": len(items),
                     "Products Left Out (too few customers)": int((pop < min_cust).sum()),
                     "Products Recommended At Least Once": int(rec["Recommended Product"].nunique()) if len(rec) else 0,
                     "Purchases Used": int(len(w))}])
for c in cov.columns:
    cov[c] = cov[c].astype("int64")

omniscope_api.write_output(rec, "recommendations")
omniscope_api.write_output(sim_df, "similar")
omniscope_api.write_output(cov, "coverage")
omniscope_api.close(f"{len(custs):,} customers, {len(items):,} products: {len(rec):,} recommendations; "
                    f"{cov['Products Recommended At Least Once'].iloc[0]:,} products recommended at least once.")
