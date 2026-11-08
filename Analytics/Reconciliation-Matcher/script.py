"""Reconciliation Matcher: match the items of two ledgers (bank statement and
cash book, invoices and payments, supplier statement and purchase ledger) and
list what is left unmatched on each side.

Matching runs in passes, each one-to-one and best match first:
  1. Exact:      same amount, same reference, dates within the window
  2. Amount:     amount within the tolerance, dates within the window
                 (closest date first, then closest amount, then reference)
  3. Group:      several items on one side with the same reference that add up
                 to one item on the other side (one payment for three invoices)

Optional fields that must agree (account, currency, entity) restrict every pass.
Amounts on side 2 can be sign-flipped (credits against debits).
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


amt_a, amt_b = opt("amount_field_a"), opt("amount_field_b")
date_a, date_b = opt("date_field_a"), opt("date_field_b")
ref_a, ref_b = opt("reference_field_a"), opt("reference_field_b")
must = list(opt("match_fields", []) or [])
tol = float(opt("tolerance", 0.0) or 0.0)
window = float(opt("date_window", 3) or 0)
flip = opt("sign", "SAME") == "OPPOSITE"
use_group = bool(opt("group_matching", True))

A = omniscope_api.read_input_records(input_number=0)
B = omniscope_api.read_input_records(input_number=1)
if A is None or B is None:
    omniscope_api.abort("Connect one side to input 1 and the other side to input 2.")
for df, f, lab in ((A, amt_a, "amount field of input 1"), (B, amt_b, "amount field of input 2")):
    if not f or f not in df.columns:
        omniscope_api.abort(f"Choose the {lab} (got '{f}').")
for df, f, lab in ((A, date_a, "input 1"), (B, date_b, "input 2"), (A, ref_a, "input 1"), (B, ref_b, "input 2")):
    if f and f not in df.columns:
        omniscope_api.abort(f"Field '{f}' is not in {lab}.")
if bool(date_a) != bool(date_b):
    omniscope_api.abort("Choose a date field on both sides, or on neither.")
if bool(ref_a) != bool(ref_b):
    omniscope_api.abort("Choose a reference field on both sides, or on neither.")
miss = [f for f in must if f not in B.columns]
if miss:
    omniscope_api.abort(f"Fields that must agree have to be in both inputs: {', '.join(miss)}")


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
    return d


def norm_ref(s):
    return s.astype(object).where(s.notna(), "").map(lambda v: re.sub(r"[^A-Z0-9]", "", str(v).upper()))


def prep(df, amt, dt, ref, sign):
    w = pd.DataFrame({"row": np.arange(len(df)), "amt": pd.to_numeric(df[amt], errors="coerce").astype("float64").to_numpy() * sign})
    w["day"] = ((to_date(df[dt]) - pd.Timestamp("1970-01-01")).dt.days.to_numpy(dtype=float)) if dt else 0.0
    w["ref"] = norm_ref(df[ref]).to_numpy() if ref else ""
    for f in must:
        w["m_" + f] = df[f].astype(object).where(df[f].notna(), "(blank)").map(str).to_numpy()
    w["cents"] = np.round(w["amt"] * 100).astype("Int64")
    return w


a = prep(A, amt_a, date_a, ref_a, 1.0)
b = prep(B, amt_b, date_b, ref_b, -1.0 if flip else 1.0)
bad_a, bad_b = int(a["amt"].isna().sum()), int(b["amt"].isna().sum())
if date_a:
    bad_a += int(a["day"].isna().sum())
    bad_b += int(b["day"].isna().sum())
mkeys = ["m_" + f for f in must]
match_a = np.full(len(a), -1)
match_b = np.full(len(b), -1)
rule_of = {}
mid = 0


def refs_agree(ra, rb):
    return (ra != "") & (rb != "") & ((ra == rb) | [((x in y) or (y in x)) and min(len(x), len(y)) >= 4 for x, y in zip(ra, rb)])


def candidates(av, bv, exact):
    av = av[av["amt"].notna() & (av["day"].notna() if date_a else True)]
    bv = bv[bv["amt"].notna() & (bv["day"].notna() if date_a else True)]
    if av.empty or bv.empty:
        return pd.DataFrame()
    if exact or tol <= 0:
        c = av.merge(bv, on=mkeys + ["cents"], suffixes=("_a", "_b"))
    else:
        step = tol * 1.000001
        av = av.assign(bin=np.floor(av["amt"] / step).astype("int64"))
        parts = []
        for off in (-1, 0, 1):
            bb = bv.assign(bin=np.floor(bv["amt"] / step).astype("int64") + off)
            parts.append(av.merge(bb, on=mkeys + ["bin"], suffixes=("_a", "_b")))
        c = pd.concat(parts, ignore_index=True)
        c = c[np.abs(c["amt_a"] - c["amt_b"]) <= tol + 1e-9]
    if date_a:
        c = c[np.abs(c["day_a"] - c["day_b"]) <= window]
    if exact and ref_a:
        c = c[(c["ref_a"] == c["ref_b"]) & (c["ref_a"] != "")]
    return c


def greedy(c, rule):
    global mid
    if c.empty:
        return 0
    c = c.assign(dd=np.abs(c["day_a"] - c["day_b"]) if date_a else 0.0, ad=np.round(np.abs(c["amt_a"] - c["amt_b"]), 6),  # rounded: float noise must not decide ties
                 rf=~refs_agree(c["ref_a"].to_numpy(), c["ref_b"].to_numpy()) if ref_a else True)
    c = c.sort_values(["dd", "ad", "rf", "row_a", "row_b"], kind="mergesort")
    n = 0
    for ra, rb in zip(c["row_a"].to_numpy(), c["row_b"].to_numpy()):
        if match_a[ra] < 0 and match_b[rb] < 0:
            mid += 1
            match_a[ra], match_b[rb] = mid, mid
            rule_of[mid] = rule
            n += 1
    return n


n_exact = greedy(candidates(a, b, True), "Exact") if ref_a else 0
n_amt = greedy(candidates(a[match_a < 0], b[match_b < 0], False), "Amount and date" if date_a else "Amount")


def group_pass(one, many, m_one, m_many, one_is_a):
    """One item on `one` side equals the sum of several unmatched items with the same reference on `many` side."""
    global mid
    n = 0
    um = many[(m_many < 0) & (many["ref"] != "") & many["amt"].notna()]
    uo = one[(m_one < 0) & (one["ref"] != "") & one["amt"].notna()]
    if um.empty or uo.empty:
        return 0
    g = um.groupby(mkeys + ["ref"]).agg(total=("amt", "sum"), k=("amt", "size"), dmin=("day", "min"), dmax=("day", "max"), rows=("row", list)).reset_index()
    g = g[g["k"] >= 2]
    c = uo.merge(g, on=mkeys + ["ref"])
    c = c[np.abs(c["amt"] - c["total"]) <= max(tol, 0.005)]
    if date_a:
        c = c[(c["day"] - c["dmin"] <= window) & (c["dmax"] - c["day"] <= window)]
    for _, r in c.sort_values("row").iterrows():
        if m_one[r["row"]] >= 0 or any(m_many[x] >= 0 for x in r["rows"]):
            continue
        mid += 1
        m_one[r["row"]] = mid
        for x in r["rows"]:
            m_many[x] = mid
        rule_of[mid] = "Group (one to many)" if one_is_a else "Group (many to one)"
        n += 1
    return n


n_group = 0
if use_group and ref_a:
    n_group += group_pass(a, b, match_a, match_b, True)
    n_group += group_pass(b, a, match_b, match_a, False)

# ---- outputs
mrows = []
for m in range(1, mid + 1):
    ia, ib = np.nonzero(match_a == m)[0], np.nonzero(match_b == m)[0]
    ta, tb = float(a["amt"].iloc[ia].sum()), float(b["amt"].iloc[ib].sum())
    rec = {"Match ID": m, "Rule": rule_of[m], "Items In 1": len(ia), "Items In 2": len(ib), "Amount 1": ta,
           "Amount 2": tb * (-1 if flip else 1), "Difference": ta - tb}
    if date_a:
        rec["Date Difference (days)"] = float(b["day"].iloc[ib].mean() - a["day"].iloc[ia].mean())
    if ref_a:
        rec["Reference 1"] = str(A[ref_a].iloc[ia[0]]) if pd.notna(A[ref_a].iloc[ia[0]]) else None
        rec["Reference 2"] = str(B[ref_b].iloc[ib[0]]) if pd.notna(B[ref_b].iloc[ib[0]]) else None
    mrows.append(rec)
mcols = ["Match ID", "Rule", "Items In 1", "Items In 2", "Amount 1", "Amount 2", "Difference"] + (["Date Difference (days)"] if date_a else []) + \
        (["Reference 1", "Reference 2"] if ref_a else [])
matches = pd.DataFrame(mrows, columns=mcols)
for c in ("Match ID", "Items In 1", "Items In 2"):
    matches[c] = matches[c].astype("int64")
for c in ("Amount 1", "Amount 2", "Difference", "Date Difference (days)"):
    if c in matches:
        matches[c] = matches[c].astype("float64")


def side_out(df, m):
    o = df.copy()
    o["Match Status"] = np.where(m > 0, "Matched", "Unmatched")
    o["Match ID"] = pd.array(np.where(m > 0, m, np.nan).astype(float), dtype="Float64").astype("Int64")
    o["Match Rule"] = [rule_of.get(int(x)) if x > 0 else None for x in m]
    return o


out_a, out_b = side_out(A, match_a), side_out(B, match_b)
summ_rows = []
for side, df_, w_, m_ in (("1", A, a, match_a), ("2", B, b, match_b)):
    for status in ("Matched", "Unmatched"):
        sel = (m_ > 0) if status == "Matched" else (m_ <= 0)
        summ_rows.append({"Side": side, "Status": status, "Items": int(sel.sum()), "Amount": float(np.nansum(w_["amt"].to_numpy()[sel])) * (-1 if (flip and side == "2") else 1)})
summ = pd.DataFrame(summ_rows)
summ["Items"] = summ["Items"].astype("int64")
summ["Amount"] = summ["Amount"].astype("float64")
by_rule = matches.groupby("Rule").size() if len(matches) else pd.Series(dtype=int)
for rl, k in by_rule.items():
    summ = pd.concat([summ, pd.DataFrame([{"Side": "Matches", "Status": rl, "Items": int(k), "Amount": float(matches[matches["Rule"] == rl]["Amount 1"].sum())}])], ignore_index=True)

omniscope_api.write_output(out_a, "side1")
omniscope_api.write_output(out_b, "side2")
omniscope_api.write_output(matches, "matches")
omniscope_api.write_output(summ, "summary")
ua, ub = int((match_a <= 0).sum()), int((match_b <= 0).sum())
omniscope_api.close(f"{mid:,} matches ({n_exact:,} exact, {n_amt:,} on amount{' and date' if date_a else ''}, {n_group:,} grouped); "
                    f"unmatched: {ua:,} in input 1, {ub:,} in input 2"
                    + (f"; {bad_a + bad_b:,} items without a valid amount or date" if bad_a + bad_b else "") + ".")
