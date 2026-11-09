"""RFM Segmentation: from a transactions table, score every customer on
Recency (days since last purchase), Frequency (number of orders) and Monetary
value (total spend), 1 to 5 (or 1 to N) by percentile, and assign a named
segment such as Champions, At Risk or Lost. A second output summarises the
segments with suggested actions.
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


customer_field = opt("customer_field")
date_field = opt("date_field")
amount_field = opt("amount_field")
order_field = opt("order_field")
analysis_date = opt("analysis_date", "")
bins = int(opt("bins", 5))
day_first = opt("day_first", True)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the transactions to the input.")
for f, label in ((customer_field, "customer"), (date_field, "date"), (amount_field, "amount")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
if order_field and order_field not in df.columns:
    omniscope_api.abort(f"Order field '{order_field}' is not in the input.")
if not 2 <= bins <= 10:
    omniscope_api.abort("Number of score bands must be between 2 and 10.")


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
    return d.dt.normalize()


t = pd.DataFrame({"cust": df[customer_field].astype(object), "date": to_date(df[date_field]),
                  "amount": pd.to_numeric(df[amount_field], errors="coerce").astype("float64")})
if order_field:
    t["order"] = df[order_field].astype(object)
skipped = int((t["cust"].isna() | t["date"].isna() | t["amount"].isna()).sum())
t = t.dropna(subset=["cust", "date", "amount"])

if analysis_date:
    ref = to_date(pd.Series([analysis_date], dtype=object)).iloc[0]
    if pd.isna(ref):
        omniscope_api.abort("Analysis date must be a date, such as 2025-12-31.")
else:
    ref = (t["date"].max() + pd.Timedelta(days=1)) if len(t) else pd.Timestamp.today().normalize()

g = t.groupby("cust", sort=True)
cust = pd.DataFrame({
    "First Purchase": g["date"].min(),
    "Last Purchase": g["date"].max(),
    "Frequency": g["order"].nunique() if order_field else g.size(),
    "Monetary": g["amount"].sum(),
})
cust["Recency (days)"] = (ref - cust["Last Purchase"]).dt.days
cust["Average Order Value"] = cust["Monetary"] / cust["Frequency"].where(cust["Frequency"] > 0)


def score(values, higher_is_better=True):
    if values.empty:
        return pd.Series([], dtype="int64")
    pct = values.rank(method="min", pct=True, ascending=higher_is_better)  # ties share the lowest band they reach
    return np.ceil(pct * bins).clip(1, bins).astype("int64")


cust["R Score"] = score(cust["Recency (days)"], higher_is_better=False)
cust["F Score"] = score(cust["Frequency"])
cust["M Score"] = score(cust["Monetary"])
cust["RFM Score"] = cust["R Score"].astype(str) + cust["F Score"].astype(str) + cust["M Score"].astype(str)
cust["RFM Total"] = cust["R Score"] + cust["F Score"] + cust["M Score"]


def to5(x):
    return 1 + (x - 1) * 4 / (bins - 1)


SEGMENTS = [
    ("Champions", "Bought recently, buy often and spend the most.", "Reward them; early access, referrals, reviews."),
    ("Loyal Customers", "Buy often and spend well, but not in the last little while.", "Upsell and loyalty schemes; ask for feedback."),
    ("Potential Loyalists", "Recent customers with average frequency and spend.", "Membership or loyalty offers; recommend related products."),
    ("New Customers", "Bought very recently, but only once or twice.", "Onboarding, welcome series, second-purchase incentive."),
    ("Need Attention", "Average on recency, frequency and spend.", "Limited-time offers based on past purchases."),
    ("About to Sleep", "Below average recency, frequency and spend.", "Reactivate with popular products and reminders."),
    ("At Risk", "Spent well and bought often, but a long time ago.", "Personal win-back campaign; find out what changed."),
    ("Can't Lose Them", "Used to be among the best customers, now gone quiet.", "Win them back with your best offer; talk to them."),
    ("Hibernating", "Low spend, low frequency, long ago.", "Low-cost reactivation; otherwise do not over-invest."),
    ("Lost", "Lowest recency, frequency and spend.", "Exclude from expensive campaigns; occasional reactivation."),
]
ORDER = [s[0] for s in SEGMENTS]


def segment(r, f, m):
    r5 = to5(r)
    fm5 = to5((f + m) / 2)
    r = math.floor(r5 + 0.5)
    fm = math.floor(fm5 + 0.5)
    if r >= 4:
        if fm >= 4:
            return "Champions"
        return "New Customers" if to5(f) <= 2 else "Potential Loyalists"
    if r == 3:
        return "Loyal Customers" if fm >= 4 else ("Need Attention" if fm == 3 else "About to Sleep")
    if r == 2:
        return "At Risk" if fm >= 3 else "Hibernating"
    return "Can't Lose Them" if fm >= 4 else ("At Risk" if fm == 3 else "Lost")


cust["Segment"] = [segment(r, f, m) for r, f, m in zip(cust["R Score"], cust["F Score"], cust["M Score"])]
desc = {s: d for s, d, _ in SEGMENTS}
cust["Segment Description"] = cust["Segment"].map(desc)

out = cust.reset_index().rename(columns={"cust": customer_field})
out = out[[customer_field, "First Purchase", "Last Purchase", "Recency (days)", "Frequency", "Monetary", "Average Order Value",
           "R Score", "F Score", "M Score", "RFM Score", "RFM Total", "Segment", "Segment Description"]]
for c in ("Recency (days)", "Frequency", "R Score", "F Score", "M Score", "RFM Total"):
    out[c] = pd.array(out[c].to_numpy(), dtype="Int64")
for c in ("Monetary", "Average Order Value"):
    out[c] = out[c].astype("float64").round(2)
for c in ("First Purchase", "Last Purchase"):
    out[c] = pd.to_datetime(out[c]).dt.tz_localize("UTC")

total_rev = out["Monetary"].sum()
seg = out.groupby("Segment").agg(Customers=(customer_field, "size"), Revenue=("Monetary", "sum"),
                                 **{"Average Recency (days)": ("Recency (days)", "mean"), "Average Frequency": ("Frequency", "mean"),
                                    "Average Monetary": ("Monetary", "mean")}).reindex(ORDER).dropna(subset=["Customers"]).reset_index()
seg["Share Of Customers"] = seg["Customers"] / max(1, len(out))
seg["Share Of Revenue"] = seg["Revenue"] / total_rev if total_rev else np.nan
seg["Description"] = seg["Segment"].map(desc)
seg["Suggested Action"] = seg["Segment"].map({s: a for s, _, a in SEGMENTS})
seg["Customers"] = seg["Customers"].astype("int64")
for c in ("Revenue", "Average Recency (days)", "Average Frequency", "Average Monetary", "Share Of Customers", "Share Of Revenue"):
    seg[c] = seg[c].astype("float64").round(4)
if seg.empty:
    seg = pd.DataFrame({"Segment": pd.Series([], dtype=object), "Customers": pd.Series([], dtype="int64"),
                        "Revenue": pd.Series([], dtype="float64"), "Average Recency (days)": pd.Series([], dtype="float64"),
                        "Average Frequency": pd.Series([], dtype="float64"), "Average Monetary": pd.Series([], dtype="float64"),
                        "Share Of Customers": pd.Series([], dtype="float64"), "Share Of Revenue": pd.Series([], dtype="float64"),
                        "Description": pd.Series([], dtype=object), "Suggested Action": pd.Series([], dtype=object)})

omniscope_api.write_output(out, "customers")
omniscope_api.write_output(seg, "segments")
omniscope_api.close(f"{len(out):,} customers scored (analysis date {ref.date()}); "
                    f"{(out['Segment'] == 'Champions').sum():,} Champions, {(out['Segment'] == 'At Risk').sum():,} At Risk"
                    + (f"; {skipped:,} rows skipped (missing customer, date or amount)." if skipped else "."))
