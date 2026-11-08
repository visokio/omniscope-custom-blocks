"""Loan Amortisation Schedule: for each loan (principal, annual interest rate,
term, start date) generate the full payment schedule: one row per payment with
opening balance, payment, interest, principal repaid, closing balance and
cumulative interest, plus a summary per loan.

Repayment types: repayment (annuity: level payments), equal principal
(declining payments) and interest only (balloon at the end). Payments
monthly, quarterly or annually; optional balloon / residual value.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


id_f = opt("loan_id_field")
principal_f = opt("principal_field")
rate_f = opt("rate_field")
term_f = opt("term_field")
start_f = opt("start_field")
balloon_f = opt("balloon_field")
type_f = opt("type_field")
default_type = opt("repayment_type", "ANNUITY")
frequency = opt("frequency", "MONTHLY")
rate_format = opt("rate_format", "AUTO")
term_unit = opt("term_unit", "MONTHS")
PER_YEAR = {"MONTHLY": 12, "QUARTERLY": 4, "ANNUAL": 1}[frequency]
STEP = {"MONTHLY": 1, "QUARTERLY": 3, "ANNUAL": 12}[frequency]

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the loans to the input.")
for f, label in ((principal_f, "principal"), (rate_f, "interest rate"), (term_f, "term")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {label} field (got '{f}').")
for f in (id_f, start_f, balloon_f, type_f):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in the input.")

P = pd.to_numeric(df[principal_f], errors="coerce").to_numpy(dtype=float)
R = pd.to_numeric(df[rate_f], errors="coerce").to_numpy(dtype=float)
T = pd.to_numeric(df[term_f], errors="coerce").to_numpy(dtype=float)
B = pd.to_numeric(df[balloon_f], errors="coerce").fillna(0.0).to_numpy(dtype=float) if balloon_f else np.zeros(len(df))
if rate_format == "PERCENT" or (rate_format == "AUTO" and np.nanmax(np.abs(R), initial=0) > 1):
    R = R / 100.0
months = T * 12 if term_unit == "YEARS" else T
if start_f:
    sd = df[start_f]
    if pd.api.types.is_datetime64_any_dtype(sd):
        starts = sd.dt.tz_localize(None) if sd.dt.tz is not None else sd
    else:
        txt = sd.astype(object).where(sd.notna(), None).astype(str).str.strip()
        iso = txt.str.match(r"^\d{4}-\d{1,2}-\d{1,2}")
        starts = pd.Series(pd.NaT, index=sd.index, dtype="datetime64[ns]")
        starts[iso] = pd.to_datetime(txt[iso], errors="coerce", format="mixed")
        starts[~iso & sd.notna()] = pd.to_datetime(txt[~iso & sd.notna()], errors="coerce", dayfirst=True, format="mixed")
else:
    starts = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
TYPES = {"annuity": "ANNUITY", "repayment": "ANNUITY", "capital and interest": "ANNUITY", "equal principal": "STRAIGHT",
         "straight": "STRAIGHT", "straight line": "STRAIGHT", "linear": "STRAIGHT", "interest only": "INTEREST_ONLY",
         "interest_only": "INTEREST_ONLY", "bullet": "INTEREST_ONLY", "balloon": "INTEREST_ONLY"}

sched, summ = [], []
for i in range(len(df)):
    lid = df[id_f].iloc[i] if id_f else i + 1
    typ = TYPES.get(str(df[type_f].iloc[i]).strip().lower(), default_type) if type_f else default_type
    p, r, mo, bal_end = P[i], R[i], months[i], B[i]
    problem = None
    if not np.isfinite(p) or p <= 0:
        problem = "Principal missing or not positive"
    elif not np.isfinite(r) or r < 0:
        problem = "Interest rate missing or negative"
    elif not np.isfinite(mo) or mo < STEP:
        problem = "Term missing or shorter than one payment period"
    elif bal_end >= p:
        problem = "Balloon must be smaller than the principal"
    if problem:
        summ.append({"Loan": lid, "Repayment Type": typ, "Status": problem})
        continue
    n = int(round(mo / STEP))
    j = r / PER_YEAR
    fin = p - bal_end  # amortised part; the balloon is repaid with the last payment
    if typ == "ANNUITY":
        # level payment that leaves exactly the balloon outstanding before the final payment's clearance
        pay_level = fin / n if j == 0 else (p - bal_end / (1 + j) ** n) * j / (1 - (1 + j) ** -n)
    bal = p
    cum_i = 0.0
    total_paid = 0.0
    first_pay = None
    for k in range(1, n + 1):
        interest = bal * j
        if typ == "ANNUITY":
            principal_part = pay_level - interest
        elif typ == "STRAIGHT":
            principal_part = fin / n
        else:
            principal_part = 0.0
        if k == n:
            principal_part = bal  # last payment clears everything, including any balloon
        pay = interest + principal_part
        close = bal - principal_part
        cum_i += interest
        total_paid += pay
        first_pay = pay if first_pay is None else first_pay
        due = (starts.iloc[i] + pd.DateOffset(months=STEP * k)) if pd.notna(starts.iloc[i]) else pd.NaT
        sched.append({"Loan": lid, "Payment Number": k, "Payment Date": due, "Opening Balance": bal, "Payment": pay,
                      "Interest": interest, "Principal Repaid": principal_part, "Closing Balance": max(close, 0.0) if abs(close) > 1e-6 else 0.0,
                      "Cumulative Interest": cum_i})
        bal = close
    last_date = (starts.iloc[i] + pd.DateOffset(months=STEP * n)) if pd.notna(starts.iloc[i]) else pd.NaT
    summ.append({"Loan": lid, "Repayment Type": typ, "Status": "OK", "Principal": p, "Annual Rate": r, "Payments": n,
                 "Regular Payment": first_pay if typ != "STRAIGHT" else np.nan, "First Payment": first_pay,
                 "Final Payment": pay, "Total Paid": total_paid, "Total Interest": cum_i,
                 "Interest As Share Of Principal": cum_i / p, "Final Payment Date": last_date})

scols = ["Loan", "Payment Number", "Payment Date", "Opening Balance", "Payment", "Interest", "Principal Repaid", "Closing Balance", "Cumulative Interest"]
so = pd.DataFrame(sched, columns=scols)
so["Payment Number"] = so["Payment Number"].astype("int64")
so["Payment Date"] = pd.to_datetime(so["Payment Date"]).dt.tz_localize("UTC")
for c in scols[3:]:
    so[c] = so[c].astype("float64").round(2)
mcols = ["Loan", "Repayment Type", "Status", "Principal", "Annual Rate", "Payments", "Regular Payment", "First Payment", "Final Payment",
         "Total Paid", "Total Interest", "Interest As Share Of Principal", "Final Payment Date"]
mo_ = pd.DataFrame(summ, columns=mcols)
mo_["Repayment Type"] = mo_["Repayment Type"].map({"ANNUITY": "Repayment (annuity)", "STRAIGHT": "Equal principal", "INTEREST_ONLY": "Interest only"})
mo_["Payments"] = pd.array(mo_["Payments"].to_numpy(dtype=float), dtype="Float64").astype("Int64")
for c in ("Principal", "Annual Rate", "Regular Payment", "First Payment", "Final Payment", "Total Paid", "Total Interest", "Interest As Share Of Principal"):
    mo_[c] = mo_[c].astype("float64").round(6 if c in ("Annual Rate", "Interest As Share Of Principal") else 2)
mo_["Final Payment Date"] = pd.to_datetime(mo_["Final Payment Date"]).dt.tz_localize("UTC")
if id_f:
    so = so.rename(columns={"Loan": str(id_f)})
    mo_ = mo_.rename(columns={"Loan": str(id_f)})

omniscope_api.write_output(so, "schedule")
omniscope_api.write_output(mo_, "summary")
bad = int((mo_["Status"] != "OK").sum())
omniscope_api.close(f"{len(mo_) - bad:,} loans scheduled ({len(so):,} payments, {frequency.lower()})" + (f"; {bad} skipped." if bad else "."))
