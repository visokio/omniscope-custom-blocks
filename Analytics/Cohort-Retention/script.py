"""Cohort Retention: group customers by the period of their first activity
(their acquisition cohort) and measure, for each later period, how many are
still active and how much they spend.

Outputs
  1 cohort matrix (long): cohort x period number with active customers,
    retention %, revenue, revenue per cohort customer and cumulative value
  2 average retention curve: by period number, weighted across cohorts
  3 customers: each customer's cohort, first / last active period, periods active
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


customer_field = opt("customer_field")
date_field = opt("date_field")
revenue_field = opt("revenue_field")
period = opt("period", "MONTH")
max_periods = int(opt("max_periods", 24))
day_first = opt("day_first", True)
FREQ = {"WEEK": "W-SUN", "MONTH": "M", "QUARTER": "Q-DEC", "YEAR": "Y-DEC"}

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the activity or order data to the input.")
for f, label in ((customer_field, "customer"), (date_field, "date")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
if revenue_field and revenue_field not in df.columns:
    omniscope_api.abort(f"Revenue field '{revenue_field}' is not in the input.")
if period not in FREQ:
    omniscope_api.abort(f"Unknown period {period}")


def to_date(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        d = s
    else:
        txt = s.astype(object).where(s.notna(), None).astype(str).str.strip()
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        d = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
        if iso.any():
            d[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
        rest = ~iso & s.notna()
        if rest.any():
            d[rest] = pd.to_datetime(txt[rest], errors="coerce", dayfirst=bool(day_first), format="mixed")
    if getattr(d.dt, "tz", None) is not None:
        d = d.dt.tz_localize(None)
    return d


freq = FREQ[period]
t = pd.DataFrame({"cust": df[customer_field].astype(object), "date": to_date(df[date_field])})
t["rev"] = pd.to_numeric(df[revenue_field], errors="coerce").fillna(0.0).astype("float64") if revenue_field else 0.0
skipped = int((t["cust"].isna() | t["date"].isna()).sum())
t = t.dropna(subset=["cust", "date"])
t["p"] = t["date"].dt.to_period(freq)
t["pord"] = t["p"].map(lambda x: x.ordinal).astype("int64") if len(t) else pd.Series([], dtype="int64")

first = t.groupby("cust")["pord"].min().rename("cohort_ord")
t = t.join(first, on="cust")
t["n"] = t["pord"] - t["cohort_ord"]
t = t[t["n"] <= max_periods]
last_ord = int(t["pord"].max()) if len(t) else 0

act = t.groupby(["cohort_ord", "n"]).agg(active=("cust", "nunique"), revenue=("rev", "sum")).reset_index()
size = act[act["n"] == 0].set_index("cohort_ord")["active"].rename("size")
act = act.join(size, on="cohort_ord")
# include periods with zero activity (up to the last observed period)
rows = []
for c, sz in size.items():
    horizon = min(max_periods, last_ord - c)
    sub = act[act["cohort_ord"] == c].set_index("n")
    cum = 0.0
    for n in range(0, horizon + 1):
        a = int(sub.loc[n, "active"]) if n in sub.index else 0
        r = float(sub.loc[n, "revenue"]) if n in sub.index else 0.0
        cum += r
        rows.append({"cohort_ord": c, "n": n, "size": int(sz), "active": a, "revenue": r, "cum": cum})
mat = pd.DataFrame(rows, columns=["cohort_ord", "n", "size", "active", "revenue", "cum"])


def label(o):
    p = pd.Period(ordinal=int(o), freq=freq)
    if period == "WEEK":
        return "w/c " + p.start_time.strftime("%Y-%m-%d")
    if period == "QUARTER":
        return f"{p.year} Q{p.quarter}"
    return str(p)


m_out = pd.DataFrame({
    "Cohort": [label(c) for c in mat["cohort_ord"]],
    "Cohort Size": pd.array(mat["size"].to_numpy(), dtype="Int64"),
    "Period Number": pd.array(mat["n"].to_numpy(), dtype="Int64"),
    "Period": [label(c + n) for c, n in zip(mat["cohort_ord"], mat["n"])],
    "Active Customers": pd.array(mat["active"].to_numpy(), dtype="Int64"),
    "Retention": (mat["active"] / mat["size"]).astype("float64"),
    "Revenue": mat["revenue"].astype("float64"),
    "Revenue Per Cohort Customer": (mat["revenue"] / mat["size"]).astype("float64"),
    "Cumulative Revenue Per Customer": (mat["cum"] / mat["size"]).astype("float64"),
})

curve = mat.groupby("n").agg(cohorts=("cohort_ord", "nunique"), size=("size", "sum"), active=("active", "sum"),
                             revenue=("revenue", "sum")).reset_index()
curve_mean = mat.assign(ret=mat["active"] / mat["size"]).groupby("n")["ret"].mean()
c_out = pd.DataFrame({
    "Period Number": pd.array(curve["n"].to_numpy(), dtype="Int64"),
    "Cohorts": pd.array(curve["cohorts"].to_numpy(), dtype="Int64"),
    "Customers In Those Cohorts": pd.array(curve["size"].to_numpy(), dtype="Int64"),
    "Active Customers": pd.array(curve["active"].to_numpy(), dtype="Int64"),
    "Retention (weighted)": (curve["active"] / curve["size"]).astype("float64"),
    "Retention (mean of cohorts)": curve["n"].map(curve_mean).astype("float64"),
    "Revenue Per Customer": (curve["revenue"] / curve["size"]).astype("float64"),
})

cg = t.groupby("cust").agg(cohort=("cohort_ord", "first"), last=("pord", "max"), periods=("pord", "nunique"), rev=("rev", "sum"))
u_out = pd.DataFrame({
    str(customer_field): cg.index.to_numpy(dtype=object),
    "Cohort": [label(c) for c in cg["cohort"]],
    "Last Active Period": [label(c) for c in cg["last"]],
    "Periods Since Acquisition": pd.array((cg["last"] - cg["cohort"]).to_numpy(), dtype="Int64"),
    "Periods Active": pd.array(cg["periods"].to_numpy(), dtype="Int64"),
    "Active In Latest Period": ["Yes" if x == last_ord else "No" for x in cg["last"]],
    "Total Revenue": cg["rev"].astype("float64").to_numpy(),
})
if not revenue_field:
    m_out = m_out.drop(columns=["Revenue", "Revenue Per Cohort Customer", "Cumulative Revenue Per Customer"])
    c_out = c_out.drop(columns=["Revenue Per Customer"])
    u_out = u_out.drop(columns=["Total Revenue"])

omniscope_api.write_output(m_out, "matrix")
omniscope_api.write_output(c_out, "curve")
omniscope_api.write_output(u_out, "customers")
r1 = c_out.loc[c_out["Period Number"] == 1, "Retention (weighted)"]
omniscope_api.close(f"{len(size):,} {period.lower()}ly cohorts, {len(u_out):,} customers"
                    + (f"; period-1 retention {float(r1.iloc[0]):.1%}" if len(r1) else "")
                    + (f"; {skipped:,} rows skipped." if skipped else "."))
