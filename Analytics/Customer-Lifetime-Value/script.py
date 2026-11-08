"""Customer Lifetime Value: historical value and a predictive CLV per customer
from order history, using the standard "buy till you die" models:

  BG/NBD (Fader, Hardie and Lee, 2005) for how often each customer will buy and
  the probability they are still active, and Gamma-Gamma for how much they will
  spend per order. Both are fitted by maximum likelihood on all customers.

Predicted CLV = expected purchases in each future month x expected order value x
margin, discounted to today. An optional holdout period checks the model:
it is fitted on the earlier data and its predicted purchases are compared with
what customers actually did in the holdout months.

Purchases are counted per customer per day (several orders on one day are one
purchase); days whose net value is zero or negative (refunds) are dropped.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi
from scipy.optimize import minimize
from scipy.special import gammaln, hyp2f1

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


cust_f = opt("customer_field")
date_f = opt("date_field")
value_f = opt("value_field")
group_fields = list(opt("group_fields", []) or [])
as_of_txt = opt("as_of", "")
horizon = int(opt("horizon_months", 12))
disc = float(opt("discount_rate", 0.1))
margin = float(opt("margin", 1.0))
holdout = int(opt("holdout_months", 0) or 0)
WEEKS_PER_MONTH = 52.0 / 12

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the orders to the input.")
for f, lab in ((cust_f, "customer"), (date_f, "order date"), (value_f, "order value")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
miss = [g for g in group_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Group fields not in the input: {', '.join(miss)}")
if not 1 <= horizon <= 240:
    omniscope_api.abort("Horizon must be 1 to 240 months.")


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
    return d.dt.normalize()


w = pd.DataFrame({"c": df[cust_f].astype(object), "d": to_date(df[date_f]),
                  "v": pd.to_numeric(df[value_f], errors="coerce").astype("float64")})
for g in group_fields:
    w[g] = df[g].astype(object).where(df[g].notna(), "(blank)")
bad_rows = int(w[["c", "d", "v"]].isna().any(axis=1).sum())
w = w.dropna(subset=["c", "d", "v"])
if w.empty:
    omniscope_api.abort("No orders with a customer, a valid date and a numeric value.")
as_of = to_date(pd.Series([as_of_txt], dtype=object)).iloc[0] if as_of_txt else w["d"].max()
if pd.isna(as_of):
    omniscope_api.abort("The 'as of' date must be a date, such as 2025-12-31.")
w = w[w["d"] <= as_of]
seg = w.sort_values("d").groupby("c")[group_fields].first() if group_fields else None
hist = w.groupby("c").agg(orders=("v", "size"), revenue=("v", "sum"))
days = w.groupby(["c", "d"], as_index=False)["v"].sum()
days = days[days["v"] > 0]


def rfm(days_df, end):
    """x = repeat purchase days, t_x = weeks first to last, T = weeks first to end, m = mean repeat value."""
    g = days_df.sort_values("d").groupby("c")
    first, last, n = g["d"].min(), g["d"].max(), g["d"].size()
    tot, fv = g["v"].sum(), g["v"].first()
    x = (n - 1).astype(float)
    m = ((tot - fv) / x).where(x > 0, np.nan)
    return pd.DataFrame({"x": x, "t_x": (last - first).dt.days / 7.0, "T": (end - first).dt.days / 7.0, "m": m, "first": first, "last": last})


def bgnbd_ll(params, x, tx, T, wt):
    r, al, a, b = np.exp(params)
    A1 = gammaln(r + x) - gammaln(r) + r * np.log(al)
    A2 = gammaln(a + b) + gammaln(b + x) - gammaln(b) - gammaln(a + b + x)
    A3 = -(r + x) * np.log(al + T)
    with np.errstate(divide="ignore", invalid="ignore"):
        A4 = np.where(x > 0, np.log(a) - np.log(np.maximum(b + x - 1, 1e-12)) - (r + x) * np.log(al + tx), -np.inf)
    return -(wt * (A1 + A2 + np.logaddexp(A3, A4))).sum() / wt.sum()


BOUNDS = [(-9.0, 9.0)] * 4


def fit_bgnbd(R):
    # identical (x, t_x, T) customers share a likelihood term: fit on the distinct rows with counts
    u = R.groupby(["x", "t_x", "T"]).size().reset_index(name="n")
    x, tx, T, wt = u["x"].to_numpy(), u["t_x"].to_numpy(), u["T"].to_numpy(), u["n"].to_numpy(dtype=float)
    scale = max(T.max(), 1e-9) / 10.0  # fit on a scaled time axis for stability; alpha scales back
    best = None
    for start in ([0.0, 0.0, 0.0, 0.0], [np.log(0.5), np.log(2.0), np.log(0.5), np.log(2.0)]):
        res = minimize(bgnbd_ll, start, args=(x, tx / scale, T / scale, wt), method="L-BFGS-B", bounds=BOUNDS,
                       options={"maxiter": 500, "ftol": 1e-12, "gtol": 1e-8})
        if best is None or res.fun < best.fun:
            best = res
    r, al, a, b = np.exp(best.x)
    at_bound = any(abs(v) > 8.99 for v in best.x)
    return {"r": r, "alpha": al * scale, "a": a, "b": b, "ll": -best.fun * wt.sum(), "ok": bool(best.success) and not at_bound}


def p_alive(P, x, tx, T):
    r, al, a, b = P["r"], P["alpha"], P["a"], P["b"]
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        term = np.where(x > 0, a / (b + x - 1) * np.exp((r + x) * (np.log(al + T) - np.log(al + tx))), 0.0)
    return 1.0 / (1.0 + term)


def expected(P, t, x, tx, T):
    """Expected purchases in the next t weeks for customers (x, t_x, T)."""
    r, al, a, b = P["r"], P["alpha"], P["a"], P["b"]
    if t <= 0:
        return np.zeros_like(x)
    z = t / (al + T + t)
    hyp = hyp2f1(r + x, b + x, a + b + x - 1, z)
    num = (a + b + x - 1) / (a - 1) * (1 - np.exp((r + x) * np.log((al + T) / (al + T + t))) * hyp)
    out = num * p_alive(P, x, tx, T)
    return np.where(np.isfinite(out), np.maximum(out, 0.0), np.nan)


def gg_ll(params, x, m):
    p, q, v = np.exp(params)
    return -(gammaln(p * x + q) - gammaln(p * x) - gammaln(q) + q * np.log(v) + (p * x - 1) * np.log(m)
             + p * x * np.log(x) - (p * x + q) * np.log(x * m + v)).mean()


def fit_gg(R):
    s = R[(R["x"] > 0) & (R["m"] > 0)]
    if len(s) < 10:
        return None
    x, m = s["x"].to_numpy(), s["m"].to_numpy()
    sc = m.mean()
    res = minimize(gg_ll, [0.0, 0.0, 0.0], args=(x, m / sc), method="L-BFGS-B", bounds=[(-9.0, 9.0)] * 3,
                   options={"maxiter": 500, "ftol": 1e-12, "gtol": 1e-8})
    p, q, v = np.exp(res.x)
    at_bound = any(abs(t) > 8.99 for t in res.x)
    return {"p": p, "q": q, "v": v * sc, "ll": -res.fun * len(s), "ok": bool(res.success) and q > 1 and not at_bound,
            "corr": float(np.corrcoef(x, m)[0, 1]) if len(s) > 2 else np.nan}


def spend(G, R, fallback):
    x, m = R["x"].to_numpy(), R["m"].to_numpy()
    if G is None or not G["ok"]:
        return np.where(x > 0, m, fallback)
    p, q, v = G["p"], G["q"], G["v"]
    pop = p * v / (q - 1)
    return np.where(x > 0, p * (v + x * np.nan_to_num(m)) / (p * x + q - 1), pop)


R = rfm(days, as_of)
if len(R) < 20 or (R["x"] > 0).sum() < 5:
    omniscope_api.abort(f"Too little history to fit the model: {len(R)} customers, {(R['x'] > 0).sum()} with repeat purchases (need at least 20 and 5).")
P = fit_bgnbd(R)
note_a = "a is very close to 1, where the expected-purchases formula is singular; predictions may be unstable" if abs(P["a"] - 1) < 1e-4 else ""
G = fit_gg(R)
first_value = days.sort_values("d").groupby("c")["v"].first()
fallback = float(first_value.mean())
E_spend = spend(G, R, fallback)
x, tx, T = R["x"].to_numpy(), R["t_x"].to_numpy(), R["T"].to_numpy()
dm = (1 + disc) ** (1 / 12) - 1
cum_prev = np.zeros(len(R))
clv = np.zeros(len(R))
purch = np.zeros(len(R))
for k in range(1, horizon + 1):
    cum = expected(P, k * WEEKS_PER_MONTH, x, tx, T)
    inc = np.maximum(np.nan_to_num(cum - cum_prev), 0.0)
    clv += inc * E_spend * margin / (1 + dm) ** k
    purch += inc
    cum_prev = cum
alive = p_alive(P, x, tx, T)

cust = pd.DataFrame({str(cust_f): R.index.to_numpy(dtype=object)})
if seg is not None:
    for g in group_fields:
        cust[g] = seg.reindex(R.index)[g].to_numpy(dtype=object)
cust["First Purchase"] = pd.to_datetime(R["first"].to_numpy()).tz_localize("UTC")
cust["Last Purchase"] = pd.to_datetime(R["last"].to_numpy()).tz_localize("UTC")
cust["Orders"] = hist["orders"].reindex(R.index).fillna(0).astype("int64").to_numpy()
cust["Purchase Days"] = (x + 1).astype("int64")
cust["Revenue To Date"] = hist["revenue"].reindex(R.index).to_numpy(dtype=float)
cust["Average Order Value"] = (days.groupby("c")["v"].mean().reindex(R.index)).to_numpy(dtype=float)
cust["Weeks Since Last Purchase"] = (T - tx).astype(float)
cust["Tenure Weeks"] = T.astype(float)
cust["Probability Active"] = alive.astype(float)
cust["Status"] = np.select([alive >= 0.7, alive >= 0.3], ["Active", "At risk"], "Likely lapsed")
cust["Expected Purchases"] = purch
cust["Expected Order Value"] = E_spend.astype(float)
cust["Predicted CLV"] = clv
cust["Historical Plus Predicted"] = cust["Revenue To Date"] * margin + cust["Predicted CLV"]
rk = cust["Predicted CLV"].rank(ascending=False, method="first")
n = len(cust)
cust["CLV Tier"] = np.select([rk <= 0.1 * n, rk <= 0.3 * n, rk <= 0.6 * n], ["Top 10%", "Next 20%", "Middle 30%"], "Bottom 40%")
cust = cust.sort_values("Predicted CLV", ascending=False, kind="mergesort").reset_index(drop=True)
for c in ("Revenue To Date", "Average Order Value", "Weeks Since Last Purchase", "Tenure Weeks", "Probability Active", "Expected Purchases",
          "Expected Order Value", "Predicted CLV", "Historical Plus Predicted"):
    cust[c] = cust[c].astype("float64")

# summary per group
sum_rows = []
parts = [({g: "All" for g in group_fields}, cust)] + ([(dict(zip(group_fields, k if isinstance(k, tuple) else (k,))), g)
                                                     for k, g in cust.groupby(group_fields, sort=True)] if group_fields else [])
for gd, g in parts:
    sum_rows.append({**gd, "Customers": len(g), "Active Share": float((g["Status"] == "Active").mean()),
                     "Revenue To Date": float(g["Revenue To Date"].sum()), "Expected Purchases": float(g["Expected Purchases"].sum()),
                     "Predicted CLV": float(g["Predicted CLV"].sum()), "Average Predicted CLV": float(g["Predicted CLV"].mean()),
                     "Median Predicted CLV": float(g["Predicted CLV"].median()),
                     "Top 10% Share Of CLV": float(g.nlargest(max(1, int(round(0.1 * len(g)))), "Predicted CLV")["Predicted CLV"].sum() / g["Predicted CLV"].sum())
                     if g["Predicted CLV"].sum() > 0 else np.nan})
summ = pd.DataFrame(sum_rows)
summ["Customers"] = summ["Customers"].astype("int64")
for c in summ.columns:
    if c not in group_fields and c != "Customers":
        summ[c] = summ[c].astype("float64")

# model parameters and checks
mrows = [("BG/NBD", "r", P["r"], "Shape of purchase-rate heterogeneity"), ("BG/NBD", "alpha", P["alpha"], "Scale of purchase rate (weeks)"),
         ("BG/NBD", "a", P["a"], "Dropout heterogeneity"), ("BG/NBD", "b", P["b"], "Dropout heterogeneity"),
         ("BG/NBD", "log-likelihood", P["ll"], "Converged" if P["ok"] else "Did not fully converge or a parameter is at its limit: the data may not suit the model"),
         ("BG/NBD", "average purchase rate per week", P["r"] / P["alpha"], "r / alpha"),
         ("BG/NBD", "average dropout probability per purchase", P["a"] / (P["a"] + P["b"]), "a / (a + b)")]
if G is not None:
    mrows += [("Gamma-Gamma", "p", G["p"], ""), ("Gamma-Gamma", "q", G["q"], ""), ("Gamma-Gamma", "v", G["v"], ""),
              ("Gamma-Gamma", "log-likelihood", G["ll"], "Converged" if G["ok"] else "Not used: did not converge or q <= 1; observed averages used"),
              ("Gamma-Gamma", "population average order value", G["p"] * G["v"] / (G["q"] - 1) if G["q"] > 1 else np.nan, "p v / (q - 1)"),
              ("Gamma-Gamma", "frequency / value correlation", G["corr"], "The model assumes this is near 0")]
mrows += [("Data", "customers", float(len(R)), ""), ("Data", "customers with repeat purchases", float((R["x"] > 0).sum()), ""),
          ("Data", "as of", np.nan, str(as_of.date())), ("Data", "horizon months", float(horizon), ""),
          ("Data", "annual discount rate", disc, ""), ("Data", "margin", margin, "")]
if note_a:
    mrows.append(("BG/NBD", "warning", np.nan, note_a))

# holdout validation
val = None
if holdout > 0:
    cut = as_of - pd.DateOffset(months=holdout)
    cal_days = days[days["d"] <= cut]
    if cal_days["c"].nunique() >= 20:
        Rc = rfm(cal_days, cut)
        if (Rc["x"] > 0).sum() >= 5:
            Pc = fit_bgnbd(Rc)
            hw = (as_of - cut).days / 7.0
            pred = expected(Pc, hw, Rc["x"].to_numpy(), Rc["t_x"].to_numpy(), Rc["T"].to_numpy())
            act = days[(days["d"] > cut) & days["c"].isin(Rc.index)].groupby("c").size().reindex(Rc.index, fill_value=0).to_numpy()
            b = np.minimum(Rc["x"].to_numpy(), 7).astype(int)
            vr = []
            for k in range(8):
                mk = b == k
                if mk.any():
                    vr.append({"Repeat Purchases Before Holdout": f"{k}+" if k == 7 else str(k), "Customers": int(mk.sum()),
                               "Actual Purchases Per Customer": float(act[mk].mean()), "Predicted Purchases Per Customer": float(np.nanmean(pred[mk]))})
            vr.append({"Repeat Purchases Before Holdout": "All", "Customers": int(len(act)), "Actual Purchases Per Customer": float(act.mean()),
                       "Predicted Purchases Per Customer": float(np.nanmean(pred))})
            val = pd.DataFrame(vr)
            mrows += [("Holdout", "holdout start", np.nan, str(cut.date())), ("Holdout", "actual purchases", float(act.sum()), ""),
                      ("Holdout", "predicted purchases", float(np.nansum(pred)), ""),
                      ("Holdout", "mean absolute error per customer", float(np.nanmean(np.abs(pred - act))), "")]
if val is None:
    val = pd.DataFrame({"Repeat Purchases Before Holdout": pd.Series([], dtype=object), "Customers": pd.Series([], dtype="int64"),
                        "Actual Purchases Per Customer": pd.Series([], dtype="float64"), "Predicted Purchases Per Customer": pd.Series([], dtype="float64")})
val["Customers"] = val["Customers"].astype("int64")
for c in ("Actual Purchases Per Customer", "Predicted Purchases Per Customer"):
    val[c] = val[c].astype("float64")
model = pd.DataFrame(mrows, columns=["Model", "Parameter", "Value", "Note"])
model["Value"] = model["Value"].astype("float64")
model["Note"] = model["Note"].replace("", None)

omniscope_api.write_output(cust, "customers")
omniscope_api.write_output(summ, "summary")
omniscope_api.write_output(model, "model")
omniscope_api.write_output(val, "validation")
tot = summ.iloc[0]
omniscope_api.close(f"{len(cust):,} customers; predicted {horizon}-month CLV {tot['Predicted CLV']:,.0f} (average {tot['Average Predicted CLV']:,.2f}); "
                    f"{tot['Active Share']:.0%} likely active" + (f"; {bad_rows:,} rows without customer, date or value skipped" if bad_rows else "") + ".")
