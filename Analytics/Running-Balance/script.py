"""Running Balance: running balance per account from an opening balance and
dated transactions (bank accounts, customer accounts, loyalty points, budgets,
stock in units), with the figures credit control and treasury ask for:

  per transaction: balance after it, and whether the account is below zero
  or below a limit;
  per account: opening and closing balance, total in and out, lowest balance
  and when, days below zero (or below the limit), and the average daily
  balance (time-weighted, from the first transaction to the as-of date).

Opening balances come from an optional second input (account, balance);
otherwise they start at zero. Transactions on the same date keep input order.
"""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


acc_f, date_f, amt_f = opt("account_field"), opt("date_field"), opt("amount_field")
o_acc, o_bal = opt("opening_account_field"), opt("opening_balance_field")
limit = float(opt("limit", 0) or 0)
as_of_txt = opt("as_of", "")

T = omniscope_api.read_input_records(input_number=0)
O = omniscope_api.read_input_records(input_number=1)
if T is None:
    omniscope_api.abort("Connect the transactions to input 1.")
for f, lab in ((acc_f, "account"), (date_f, "date"), (amt_f, "amount")):
    if not f or f not in T.columns:
        omniscope_api.abort(f"Choose the {lab} field (got '{f}').")
opening = {}
if O is not None:
    for f, lab in ((o_acc, "account"), (o_bal, "opening balance")):
        if not f or f not in O.columns:
            omniscope_api.abort(f"Choose the {lab} field of input 2.")
    for a, b in zip(O[o_acc].astype(object).map(str), pd.to_numeric(O[o_bal], errors="coerce").fillna(0)):
        opening[a] = opening.get(a, 0.0) + float(b)


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
    return d.astype("datetime64[ns]").dt.normalize()


w = pd.DataFrame({"a": T[acc_f].astype(object).where(T[acc_f].notna(), "(blank)").map(str), "d": to_date(T[date_f]),
                  "x": pd.to_numeric(T[amt_f], errors="coerce").astype("float64"), "row": np.arange(len(T))})
bad = int(w[["d", "x"]].isna().any(axis=1).sum())
w = w.dropna(subset=["d", "x"]).sort_values(["a", "d", "row"], kind="mergesort")
as_of = to_date(pd.Series([as_of_txt], dtype=object)).iloc[0] if as_of_txt else (w["d"].max() if len(w) else pd.NaT)
if as_of_txt and pd.isna(as_of):
    omniscope_api.abort("The as-of date must be a date, such as 2025-11-30.")
w["open"] = w["a"].map(lambda a: opening.get(a, 0.0))
w["bal"] = w.groupby("a")["x"].cumsum() + w["open"]
bal = pd.Series(np.nan, index=range(len(T)))
bal[w["row"].to_numpy()] = w["bal"].to_numpy()
out = T.copy()
out["Balance After"] = bal.to_numpy()
out["Below Zero"] = np.where(bal.isna(), None, np.where(bal < 0, "Yes", "No"))
if limit:
    out["Below Limit"] = np.where(bal.isna(), None, np.where(bal < -abs(limit) if limit > 0 else bal < limit, "Yes", "No"))
srows = []
thr = -abs(limit) if limit else 0.0
for a, g in w.groupby("a", sort=True):
    daily = g.groupby("d")["bal"].last()
    days = pd.date_range(daily.index.min(), max(as_of, daily.index.max()), freq="D")
    dbal = daily.reindex(days).ffill().to_numpy()
    srows.append({str(acc_f): a, "Opening Balance": float(g["open"].iloc[0]), "Transactions": int(len(g)), "Total In": float(g["x"][g["x"] > 0].sum()),
                  "Total Out": float(-g["x"][g["x"] < 0].sum()), "Closing Balance": float(g["bal"].iloc[-1]), "Lowest Balance": float(g["bal"].min()),
                  "Lowest On": g.loc[g["bal"].idxmin(), "d"], "Days Below Zero": int((dbal < 0).sum()),
                  **({"Days Below Limit": int((dbal < thr).sum())} if limit else {}), "Average Daily Balance": float(dbal.mean()),
                  "First Date": days[0], "Last Date": days[-1]})
summ = pd.DataFrame(srows)
if len(summ):
    for c in ("Lowest On", "First Date", "Last Date"):
        summ[c] = pd.to_datetime(summ[c]).dt.tz_localize("UTC")
    for c in summ.columns:
        if c in ("Transactions", "Days Below Zero", "Days Below Limit"):
            summ[c] = summ[c].astype("int64")
        elif c not in (str(acc_f), "Lowest On", "First Date", "Last Date"):
            summ[c] = summ[c].astype("float64")
    summ = summ.sort_values("Lowest Balance", kind="mergesort").reset_index(drop=True)
out["Balance After"] = out["Balance After"].astype("float64")
omniscope_api.write_output(out, "transactions")
omniscope_api.write_output(summ, "accounts")
neg = int((summ["Days Below Zero"] > 0).sum()) if len(summ) else 0
omniscope_api.close(f"{len(w):,} transactions on {len(summ):,} accounts; {neg:,} accounts went below zero" + (f"; {bad:,} rows without a valid date or amount skipped" if bad else "") + ".")
