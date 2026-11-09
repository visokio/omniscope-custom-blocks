"""Investment Appraisal: compare projects, capital requests or business cases
from their cash flows.

  Per project: NPV at the discount rate, IRR (or XIRR on actual dates), MIRR
  (finance and reinvestment at the discount rate), payback and discounted
  payback (interpolated within the period), profitability index (PV of
  inflows / PV of outflows), totals, rank by NPV and an accept / reject flag.
  Projects whose cash flows change sign more than once can have several IRRs;
  they are flagged and the IRR nearest the discount rate is reported.

Timing: by period number (0 = now, 1 = end of year 1...) with a rate per
period, or by date (XNPV / XIRR: annual rate, actual days / 365, discounted to
the first date of each project). Outputs also the discounted cash flows and an
NPV profile (NPV at rates from 0% to the maximum, for charts).
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


proj_f = opt("project_field")
time_f = opt("time_field")
amt_f = opt("amount_field")
timing = opt("timing", "PERIOD")
rate = float(opt("discount_rate", 0.08))
rate_f = opt("rate_field")
max_rate = float(opt("profile_max_rate", 0.3))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the cash flows to the input.")
for f, lab in ((proj_f, "project"), (time_f, "period or date"), (amt_f, "amount")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
if rate_f and rate_f not in df.columns:
    omniscope_api.abort(f"Field '{rate_f}' is not in the input.")
if rate <= -1:
    omniscope_api.abort("The discount rate must be above -100%.")


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
    return d.astype("datetime64[ns]")


w = pd.DataFrame({"p": df[proj_f].astype(object).where(df[proj_f].notna(), "(blank)").map(str),
                  "a": pd.to_numeric(df[amt_f], errors="coerce").astype("float64")})
if timing == "DATE":
    w["d"] = to_date(df[time_f])
else:
    w["t"] = pd.to_numeric(df[time_f], errors="coerce").astype("float64")
if rate_f:
    w["r"] = pd.to_numeric(df[rate_f], errors="coerce").astype("float64")
bad = int(w[["a", "d" if timing == "DATE" else "t"]].isna().any(axis=1).sum())
w = w.dropna(subset=["a", "d" if timing == "DATE" else "t"])


def npv(r, t, a):
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return float((a / (1 + r) ** t).sum())


def irrs(t, a):
    """All IRRs between -99% and 1000% found by scanning for sign changes and bisecting."""
    grid = np.concatenate([np.linspace(-0.99, 1, 2000), np.linspace(1.001, 10, 900)])
    vals = np.array([npv(r, t, a) for r in grid])
    roots = []
    for i in range(len(grid) - 1):
        v0, v1 = vals[i], vals[i + 1]
        if not (np.isfinite(v0) and np.isfinite(v1)):
            continue
        if v0 == 0:
            roots.append(grid[i])
        elif v0 * v1 < 0:
            lo, hi = grid[i], grid[i + 1]
            for _ in range(100):
                mid = (lo + hi) / 2
                vm = npv(mid, t, a)
                if (vm > 0) == (npv(lo, t, a) > 0):
                    lo = mid
                else:
                    hi = mid
            roots.append((lo + hi) / 2)
    return roots


def payback(t, cf):
    cum = np.cumsum(cf)
    for i in range(len(cf)):
        if cum[i] >= 0 and (i == 0 or cum[i - 1] < 0):
            if i == 0:
                return float(t[0])
            frac = -cum[i - 1] / cf[i] if cf[i] else 0.0
            return float(t[i - 1] + frac * (t[i] - t[i - 1]))
    return np.nan


prows, frows, nrows = [], [], []
for p, g in w.groupby("p", sort=True):
    if timing == "DATE":
        g = g.groupby("d", as_index=False).agg(a=("a", "sum"), **({"r": ("r", "first")} if rate_f else {})).sort_values("d")
        t0 = g["d"].min()
        t = ((g["d"] - t0).dt.days / 365.0).to_numpy()
    else:
        g = g.groupby("t", as_index=False).agg(a=("a", "sum"), **({"r": ("r", "first")} if rate_f else {})).sort_values("t")
        t = g["t"].to_numpy()
    a = g["a"].to_numpy()
    r = float(g["r"].dropna().iloc[0]) if rate_f and g["r"].notna().any() else rate
    disc = 1 / (1 + r) ** t
    pv = a * disc
    v_npv = float(pv.sum())
    roots = irrs(t, a)
    signs = np.sign(a[a != 0])
    changes = int((np.diff(signs) != 0).sum()) if len(signs) > 1 else 0
    irr = min(roots, key=lambda x: abs(x - r)) if roots else np.nan
    pv_in, pv_out = float(pv[pv > 0].sum()), float(-pv[pv < 0].sum())
    n_end = t.max() if len(t) else 0
    fv_in = float((np.where(a > 0, a, 0) * (1 + r) ** (n_end - t)).sum())
    mirr = (fv_in / pv_out) ** (1 / n_end) - 1 if pv_out > 0 and fv_in > 0 and n_end > 0 else np.nan
    pb = payback(t, a)
    dpb = payback(t, pv)
    prows.append({"Project": p, "Discount Rate": r, "Cash Flows": len(a), "Total Outflows": float(-a[a < 0].sum()), "Total Inflows": float(a[a > 0].sum()),
                  "Net Cash Flow": float(a.sum()), "NPV": v_npv, "IRR": irr, "MIRR": mirr, "Profitability Index": pv_in / pv_out if pv_out > 0 else np.nan,
                  "Payback": pb, "Discounted Payback": dpb, "Sign Changes": changes,
                  "IRR Note": None if changes <= 1 else (f"{len(roots)} IRRs found ({', '.join(f'{x:.1%}' for x in roots[:3])}); use NPV" if len(roots) > 1 else "Several sign changes; IRR may not be unique"),
                  "Decision": "Accept" if v_npv > 0 else "Reject", "Horizon": float(n_end)})
    cum, cum_pv = np.cumsum(a), np.cumsum(pv)
    for i in range(len(a)):
        rec = {"Project": p, "Time": float(t[i]), "Cash Flow": float(a[i]), "Discount Factor": float(disc[i]), "Present Value": float(pv[i]),
               "Cumulative Cash Flow": float(cum[i]), "Cumulative Present Value": float(cum_pv[i])}
        if timing == "DATE":
            rec["Date"] = g["d"].iloc[i]
        frows.append(rec)
    for rr in np.round(np.arange(0, max_rate + 1e-9, 0.01), 4):
        nrows.append({"Project": p, "Rate": float(rr), "NPV": npv(rr, t, a)})

pcols = ["Project", "Discount Rate", "Cash Flows", "Total Outflows", "Total Inflows", "Net Cash Flow", "NPV", "IRR", "MIRR", "Profitability Index", "Payback",
         "Discounted Payback", "Horizon", "Sign Changes", "IRR Note", "Decision"]
proj = pd.DataFrame(prows, columns=pcols)
proj["Rank By NPV"] = proj["NPV"].rank(ascending=False, method="min").astype("int64") if len(proj) else pd.Series([], dtype="int64")
proj = proj.sort_values("Rank By NPV", kind="mergesort").reset_index(drop=True).rename(columns={"Project": str(proj_f)})
for c in ("Cash Flows", "Sign Changes"):
    proj[c] = proj[c].astype("int64")
for c in ("Discount Rate", "Total Outflows", "Total Inflows", "Net Cash Flow", "NPV", "IRR", "MIRR", "Profitability Index", "Payback", "Discounted Payback", "Horizon"):
    proj[c] = proj[c].astype("float64")
fcols = ["Project"] + (["Date"] if timing == "DATE" else []) + ["Time", "Cash Flow", "Discount Factor", "Present Value", "Cumulative Cash Flow", "Cumulative Present Value"]
flows = pd.DataFrame(frows, columns=fcols).rename(columns={"Project": str(proj_f), "Time": "Years From Start" if timing == "DATE" else "Period"})
if timing == "DATE" and len(flows):
    flows["Date"] = pd.to_datetime(flows["Date"]).dt.tz_localize("UTC")
for c in flows.columns[1:]:
    if c != "Date":
        flows[c] = flows[c].astype("float64")
prof = pd.DataFrame(nrows, columns=["Project", "Rate", "NPV"]).rename(columns={"Project": str(proj_f)})
for c in ("Rate", "NPV"):
    prof[c] = prof[c].astype("float64")

omniscope_api.write_output(proj, "projects")
omniscope_api.write_output(flows, "cashflows")
omniscope_api.write_output(prof, "npv_profile")
acc = int((proj["Decision"] == "Accept").sum())
omniscope_api.close(f"{len(proj):,} project(s) at {rate:.1%}" + (" (or their own rate)" if rate_f else "") + f": {acc} with positive NPV"
                    + (f"; best: {proj.iloc[0][str(proj_f)]} (NPV {proj.iloc[0]['NPV']:,.0f})" if len(proj) else "")
                    + (f"; {bad:,} rows without a valid time or amount skipped" if bad else "") + ".")
