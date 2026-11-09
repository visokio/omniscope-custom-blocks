"""Likert Survey Summary: turn wide survey responses (one row per respondent,
one column per statement, answers such as "Strongly agree" or 1 to 5) into
the standard survey tables: answer distribution per question, mean score,
top-2-box and bottom-2-box shares, net score and neutral share, optionally per
segment (department, region), plus a tidy long table for further analysis.
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


questions = opt("question_fields", []) or []
segments = opt("segment_fields", []) or []
scale = opt("scale", "AGREE5")
custom = opt("custom_labels", "")
box = int(opt("box_size", 2))
min_n = int(opt("min_responses", 5))

SCALES = {
    "AGREE5": ["Strongly disagree", "Disagree", "Neither agree nor disagree", "Agree", "Strongly agree"],
    "AGREE4": ["Strongly disagree", "Disagree", "Agree", "Strongly agree"],
    "SAT5": ["Very dissatisfied", "Dissatisfied", "Neither satisfied nor dissatisfied", "Satisfied", "Very satisfied"],
    "LIKELY5": ["Very unlikely", "Unlikely", "Neither likely nor unlikely", "Likely", "Very likely"],
    "FREQ5": ["Never", "Rarely", "Sometimes", "Often", "Always"],
}
NO_ANSWER = {"na", "n a", "dont know", "prefer not to say", "not applicable"}

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the survey responses to the input.")
if not questions:
    omniscope_api.abort("Choose the question fields.")
miss = [f for f in list(questions) + list(segments) if f not in df.columns]
if miss:
    omniscope_api.abort(f"Fields not in the input: {', '.join(miss)}")

if scale == "CUSTOM":
    labels = [t.strip() for t in re.split(r"[,;\n]", custom or "") if t.strip()]
    if len(labels) < 2:
        omniscope_api.abort("List at least two answer labels, lowest first, for a custom scale.")
elif scale == "NUMERIC":
    labels = None
else:
    labels = SCALES.get(scale)
    if labels is None:
        omniscope_api.abort(f"Unknown scale {scale}")


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", str(s).lower().replace("’", "'").replace("'", "")).strip()


if labels is not None:
    k = len(labels)
    lookup = {norm(l): i + 1 for i, l in enumerate(labels)}
    for i in range(1, k + 1):
        lookup[str(i)] = i  # numbers are accepted too
    mid = (k + 1) / 2
    for l_ in labels:
        if norm(l_).startswith("neither"):
            lookup["neutral"] = labels.index(l_) + 1
            lookup["neither"] = labels.index(l_) + 1
else:
    allv = pd.concat([pd.to_numeric(df[q], errors="coerce") for q in questions]).dropna()
    lo, hi = (int(allv.min()), int(allv.max())) if len(allv) else (1, 5)
    labels = [str(i) for i in range(lo, hi + 1)]
    k = len(labels)
    lookup = {str(v): v - lo + 1 for v in range(lo, hi + 1)}
    mid = (k + 1) / 2


def score(v):
    if v is None or (isinstance(v, float) and v != v):
        return np.nan, "No answer"
    if isinstance(v, (int, float, np.integer, np.floating)) and float(v).is_integer():
        key = str(int(v))
    else:
        key = norm(v)
    if key in lookup:
        return lookup[key], labels[lookup[key] - 1]
    if key in NO_ANSWER:
        return np.nan, "No answer"
    return np.nan, "Unrecognised"


rows = []
seg_vals = df[segments].astype(object).where(df[segments].notna(), "(blank)") if segments else None
for q in questions:
    col = df[q].tolist()
    for r, v in enumerate(col):
        sc, lab = score(v)
        rec = {"Respondent Row": r + 1, "Question": str(q), "Answer": lab, "Score": sc}
        if segments:
            for sgf in segments:
                rec[sgf] = seg_vals.iloc[r][sgf]
        rows.append(rec)
long = pd.DataFrame(rows, columns=["Respondent Row"] + list(segments) + ["Question", "Answer", "Score"])
long["Respondent Row"] = long["Respondent Row"].astype("int64")
long["Score"] = long["Score"].astype("float64")

keys = list(segments) + ["Question"]
dist_rows, sum_rows = [], []
for key, g in long.groupby(keys, sort=False):
    key = key if isinstance(key, tuple) else (key,)
    kd = dict(zip(keys, key))
    gv = g[g["Score"].notna()]
    n = len(gv)
    counts = gv["Score"].value_counts().reindex(range(1, k + 1), fill_value=0)
    for i in range(1, k + 1):
        share = counts[i] / n if n else np.nan
        side = -1 if i < mid else (1 if i > mid else 0)
        dist_rows.append({**kd, "Answer": labels[i - 1], "Answer Order": i, "Count": int(counts[i]), "Share": share,
                          "Diverging Share": side * share if n else np.nan})
    top = counts.iloc[k - box:].sum() / n if n else np.nan  # positional: the highest `box` answers
    bottom = counts.iloc[:box].sum() / n if n else np.nan
    neutral = counts.loc[int(mid)] / n if (n and k % 2 == 1) else (0.0 if n else np.nan)
    sum_rows.append({**kd, "Responses": n, "No Answer": int((g["Answer"] == "No answer").sum()),
                     "Unrecognised": int((g["Answer"] == "Unrecognised").sum()),
                     "Mean Score": gv["Score"].mean() if n else np.nan,
                     f"Top {box} Box": top, f"Bottom {box} Box": bottom, "Neutral": neutral,
                     "Net Score": (top - bottom) if n else np.nan,
                     "Reliable": "Yes" if n >= min_n else f"No (fewer than {min_n} responses)"})

dist = pd.DataFrame(dist_rows, columns=keys + ["Answer", "Answer Order", "Count", "Share", "Diverging Share"])
summ = pd.DataFrame(sum_rows, columns=keys + ["Responses", "No Answer", "Unrecognised", "Mean Score", f"Top {box} Box",
                                              f"Bottom {box} Box", "Neutral", "Net Score", "Reliable"])
for c in ("Answer Order", "Count"):
    dist[c] = dist[c].astype("int64")
for c in ("Share", "Diverging Share"):
    dist[c] = dist[c].astype("float64")
for c in ("Responses", "No Answer", "Unrecognised"):
    summ[c] = summ[c].astype("int64")
for c in ("Mean Score", f"Top {box} Box", f"Bottom {box} Box", "Neutral", "Net Score"):
    summ[c] = summ[c].astype("float64")
if len(summ):
    summ["Rank (by net score)"] = pd.array(summ.groupby(list(segments) if segments else (lambda _: 0))["Net Score"]
                                            .rank(ascending=False, method="min").to_numpy(), dtype="Float64").astype("Int64")
else:
    summ["Rank (by net score)"] = pd.array([], dtype="Int64")

omniscope_api.write_output(summ, "summary")
omniscope_api.write_output(dist, "distribution")
omniscope_api.write_output(long, "responses")
unrec = int((long["Answer"] == "Unrecognised").sum())
omniscope_api.close(f"{len(df):,} respondents, {len(questions)} questions summarised"
                    + (f" by {', '.join(segments)}" if segments else "") + (f"; {unrec:,} unrecognised answers." if unrec else "."))
