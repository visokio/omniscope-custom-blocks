"""Benford's Law Test: compare the leading digits of amounts with the
distribution Benford's law predicts, overall or per group (department,
supplier, employee), as a screening test for fraud and data problems.

Tests: first digit (1-9), first two digits (10-99), second digit (0-9).
For each group: chi-square statistic and p-value, mean absolute deviation (MAD)
with Nigrini's conformity bands, the most over-represented digits, and the
records carrying those digits for follow-up. Pure Python (no scipy).
"""
import math

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


value_field = opt("value_field")
test = opt("test", "FIRST")
group_fields = opt("group_fields", []) or []
min_value = float(opt("min_value", 10))
min_records = int(opt("min_records", 100))
z_threshold = float(opt("z_threshold", 1.96))
p_threshold = float(opt("p_threshold", 0.01))

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the amounts to test to the input.")
if not value_field or value_field not in df.columns:
    omniscope_api.abort(f"Choose the amount field (got '{value_field}').")
miss = [g for g in group_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Group fields not in the input: {', '.join(miss)}")

if test == "FIRST":
    digits = np.arange(1, 10)
    expected = np.log10(1 + 1 / digits)
    bands = [(0.006, "Close conformity"), (0.012, "Acceptable conformity"), (0.015, "Marginally acceptable conformity")]
elif test == "FIRST_TWO":
    digits = np.arange(10, 100)
    expected = np.log10(1 + 1 / digits)
    bands = [(0.0012, "Close conformity"), (0.0018, "Acceptable conformity"), (0.0022, "Marginally acceptable conformity")]
elif test == "SECOND":
    digits = np.arange(0, 10)
    expected = np.array([sum(math.log10(1 + 1 / (10 * k + d)) for k in range(1, 10)) for d in digits])
    bands = [(0.008, "Close conformity"), (0.010, "Acceptable conformity"), (0.012, "Marginally acceptable conformity")]
else:
    omniscope_api.abort(f"Unknown test {test}")
    raise SystemExit


def gammaincc(a, x):
    """Regularised upper incomplete gamma Q(a, x) (Numerical Recipes)."""
    if x <= 0:
        return 1.0
    gln = math.lgamma(a)
    if x < a + 1:
        ap, s = a, 1.0 / a
        d = s
        for _ in range(1000):
            ap += 1
            d *= x / ap
            s += d
            if abs(d) < abs(s) * 1e-15:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - gln)
    b = x + 1 - a
    c, d = 1e300, 1 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1 / (d if abs(d) > 1e-300 else 1e-300)
        c = b + an / c
        c = c if abs(c) > 1e-300 else 1e-300
        de = d * c
        h *= de
        if abs(de - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


vals = pd.to_numeric(df[value_field], errors="coerce").abs()
usable = vals.notna() & (vals >= max(min_value, 1e-12))


def digit_of(v):
    """Leading digits as integers, from the decimal representation (robust to float noise)."""
    mant = np.floor(np.log10(v))
    scaled = v / np.power(10.0, mant)
    scaled = np.round(scaled, 9)
    if test == "FIRST":
        return np.floor(scaled).astype(int)
    two = np.floor(np.round(scaled * 10, 7)).astype(int)
    two = np.clip(two, 10, 99)
    return two if test == "FIRST_TWO" else two % 10


d = pd.Series(np.nan, index=df.index)
if usable.any():
    d[usable] = digit_of(vals[usable].to_numpy(dtype=float))

if group_fields:
    keys = [df[c].astype(object).where(df[c].notna(), "(blank)") for c in group_fields]
    groups = [(k, d.index[v]) for k, v in d.groupby(keys, sort=True).indices.items()]
else:
    groups = [((), d.index)]

digit_rows, summary_rows, flagged_idx, flagged_digit = [], [], [], {}
for key, idx in groups:
    key = key if isinstance(key, tuple) else (key,)
    gd = {c: key[i] for i, c in enumerate(group_fields)}
    sub = d.loc[idx].dropna().astype(int)
    n = len(sub)
    counts = sub.value_counts().reindex(digits, fill_value=0).to_numpy()
    obs = counts / n if n else np.zeros(len(digits))
    exp_counts = expected * n
    with np.errstate(divide="ignore", invalid="ignore"):
        se = np.sqrt(expected * (1 - expected) / n) if n else np.full(len(digits), np.nan)
        # z with continuity correction (Nigrini)
        z = (np.abs(obs - expected) - (1 / (2 * n) if n else 0)) / se
    z = np.where(np.abs(obs - expected) < (1 / (2 * n) if n else 0), 0.0, z)
    over = (obs > expected) & (z > z_threshold)
    for i, dig in enumerate(digits):
        digit_rows.append({**gd, "Digit": int(dig), "Count": int(counts[i]), "Observed Share": float(obs[i]),
                           "Expected Share": float(expected[i]), "Difference": float(obs[i] - expected[i]),
                           "Z Statistic": float(z[i]) if n else np.nan,
                           "Flag": ("Over-represented" if over[i] else ("Under-represented" if (obs[i] < expected[i] and z[i] > z_threshold) else ""))})
    chi = float(np.sum((counts - exp_counts) ** 2 / exp_counts)) if n else np.nan
    dof = len(digits) - 1
    p = gammaincc(dof / 2, chi / 2) if n else np.nan
    mad = float(np.mean(np.abs(obs - expected))) if n else np.nan
    if not n:
        verdict = "No usable values"
    elif n < min_records:
        verdict = f"Too few values to judge (fewer than {min_records})"
    else:
        verdict = next((label for lim, label in bands if mad <= lim), "Nonconformity")
        if verdict == "Nonconformity" and not p < p_threshold:
            # MAD bands assume large samples; small groups deviate by chance
            verdict = "Nonconformity on MAD only (chi-square not significant)"
    top = [int(digits[i]) for i in np.argsort(-(obs - expected))[:3] if over[i]]
    exp_mad = float(math.sqrt(2 / math.pi) * np.mean(np.sqrt(expected * (1 - expected) / n))) if n else np.nan
    summary_rows.append({**gd, "Values Tested": n, "Chi-Square": chi, "Degrees Of Freedom": dof, "P Value": p, "MAD": mad,
                         "Expected MAD If Conforming": exp_mad,
                         "Conformity": verdict, "Over-represented Digits": ", ".join(map(str, top))})
    if n >= min_records and verdict == "Nonconformity" and top:
        sel = sub[sub.isin(top)].index
        flagged_idx.extend(sel)
        for r in sel:
            flagged_digit[r] = int(sub[r])

dig = pd.DataFrame(digit_rows, columns=list(group_fields) + ["Digit", "Count", "Observed Share", "Expected Share", "Difference", "Z Statistic", "Flag"])
dig["Digit"] = dig["Digit"].astype("int64")
dig["Count"] = dig["Count"].astype("int64")
summ = pd.DataFrame(summary_rows, columns=list(group_fields) + ["Values Tested", "Chi-Square", "Degrees Of Freedom", "P Value", "MAD",
                                                               "Expected MAD If Conforming", "Conformity", "Over-represented Digits"])
summ["Values Tested"] = summ["Values Tested"].astype("int64")
summ["Degrees Of Freedom"] = summ["Degrees Of Freedom"].astype("int64")
for c in ("Chi-Square", "P Value", "MAD", "Expected MAD If Conforming"):
    summ[c] = summ[c].astype("float64")
flag = df.loc[flagged_idx].copy()
flag["Tested Digits"] = pd.array([flagged_digit[i] for i in flagged_idx], dtype="Int64")
flag["Reason"] = "Digits over-represented in a nonconforming group"

omniscope_api.write_output(dig, "digits")
omniscope_api.write_output(summ, "summary")
omniscope_api.write_output(flag, "flagged")
non = int((summ["Conformity"] == "Nonconformity").sum())
omniscope_api.close(f"{int(usable.sum()):,} values tested ({test.replace('_', ' ').lower()} digit test) in {len(summ):,} group(s); "
                    f"{non} nonconforming; {len(flag):,} records flagged.")
