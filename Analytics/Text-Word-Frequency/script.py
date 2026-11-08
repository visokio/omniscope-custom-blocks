"""Text Word Frequency: count the words and phrases (n-grams) in a text field,
such as survey comments, complaints, reviews or ticket descriptions, overall
and per group, and find the words most distinctive of each group.

  Tokenising: lower case, letters (and apostrophes / hyphens inside words),
  optional numbers; English stop words removed (plus your own); phrases are
  formed from consecutive remaining words.
  Counts: occurrences, the number of rows (documents) using the term, and the
  share of rows.
  Distinctive terms: weighted log-odds ratio with an informative Dirichlet
  prior (Monroe, Colaresi and Quinn, 2008), as a z-score of each group against
  all the others; z above 1.96 is flagged.
"""
import re
from collections import Counter

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


text_f = opt("text_field")
group_fields = list(opt("group_fields", []) or [])
max_n = int(opt("max_ngram", 2))
min_len = int(opt("min_word_length", 2))
use_stop = bool(opt("remove_stop_words", True))
extra_stop = opt("extra_stop_words", "")
keep_numbers = bool(opt("keep_numbers", False))
min_docs = int(opt("min_documents", 2))
top_n = int(opt("top_n", 0) or 0)

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the text data to the input.")
if not text_f or text_f not in df.columns:
    omniscope_api.abort(f"Choose the text field (got '{text_f}').")
miss = [g for g in group_fields if g not in df.columns]
if miss:
    omniscope_api.abort(f"Group fields not in the input: {', '.join(miss)}")
if not 1 <= max_n <= 4:
    omniscope_api.abort("Longest phrase must be 1 to 4 words.")

STOP = set("""a about above after again against all almost also am an and any are aren't as at be because been before being below between both but by
can can't cannot could couldn't did didn't do does doesn't doing don't down during each either else even ever every few for from further get gets got
had hadn't has hasn't have haven't having he he'd he'll he's her here here's hers herself him himself his how how's however i i'd i'll i'm i've if in into
is isn't it it's its itself just let's like ll me might more most much must mustn't my myself neither no nor not now of off on once one only or other
ought our ours ourselves out over own per quite rather re really same shan't she she'd she'll she's should shouldn't so some such than that that's the
their theirs them themselves then there there's these they they'd they'll they're they've this those though through to too under until up upon us
very was wasn't we we'd we'll we're we've were weren't what what's when when's where where's whether which while who who's whom whose why why's will
with within without won't would wouldn't yet you you'd you'll you're you've your yours yourself yourselves s t d m ve""".split())
if not use_stop:
    STOP = set()
STOP |= {w.strip().lower() for w in re.split(r"[,;\n]", extra_stop or "") if w.strip()}
TOKEN = re.compile(r"[a-z0-9]+(?:['\-][a-z0-9]+)*")


def tokens(t):
    if t is None or (isinstance(t, float) and t != t):
        return []
    t = str(t).lower().replace("’", "'").replace("‘", "'")
    out = []
    for w in TOKEN.findall(t):
        if w in STOP or len(w) < min_len:
            continue
        if not keep_numbers and any(ch.isdigit() for ch in w):
            continue
        out.append(w)
    return out


def grams(tok):
    g = list(tok)
    for n in range(2, max_n + 1):
        g += [" ".join(tok[i:i + n]) for i in range(len(tok) - n + 1)]
    return g


gkey = pd.Series([()] * len(df), index=df.index) if not group_fields else \
    pd.Series(list(zip(*[df[g].astype(object).where(df[g].notna(), "(blank)").map(str) for g in group_fields])), index=df.index)
tok_lists = [tokens(t) for t in df[text_f].tolist()]
occ = {}    # group -> Counter of occurrences
docs = {}   # group -> Counter of documents
ndocs = Counter()
for gk, tl in zip(gkey.tolist(), tok_lists):
    gl = grams(tl)
    occ.setdefault(gk, Counter()).update(gl)
    docs.setdefault(gk, Counter()).update(set(gl))
    ndocs[gk] += 1
all_occ, all_docs = Counter(), Counter()
for gk in occ:
    all_occ.update(occ[gk])
    all_docs.update(docs[gk])
total_docs = sum(ndocs.values())
keep = {w for w, c in all_docs.items() if c >= min_docs}

rows = []
groups = sorted(occ) if group_fields else [()]
N_all = float(sum(all_occ[w] for w in keep)) or 1.0
alpha0 = 500.0
for gk in ([()] if not group_fields else groups):
    oc = occ.get(gk, Counter()) if group_fields else all_occ
    dc = docs.get(gk, Counter()) if group_fields else all_docs
    nd = ndocs.get(gk, 0) if group_fields else total_docs
    terms = [w for w in keep if dc.get(w, 0) > 0]
    if not terms:
        continue
    y_i = np.array([oc[w] for w in terms], dtype=float)
    d_i = np.array([dc[w] for w in terms], dtype=float)
    rec = {"term": terms, "occ": y_i, "docs": d_i, "share": d_i / nd if nd else np.nan}
    if group_fields:
        y_all = np.array([all_occ[w] for w in terms], dtype=float)
        y_j = y_all - y_i
        n_i = float(sum(oc[w] for w in keep))
        n_j = N_all - n_i
        a_w = alpha0 * y_all / N_all
        with np.errstate(divide="ignore", invalid="ignore"):
            delta = (np.log((y_i + a_w) / (n_i + alpha0 - y_i - a_w)) - np.log((y_j + a_w) / (n_j + alpha0 - y_j - a_w)))
            z = delta / np.sqrt(1 / (y_i + a_w) + 1 / (y_j + a_w))
        rest_docs = total_docs - nd
        rest_share = np.array([(all_docs[w] - dc[w]) for w in terms], dtype=float) / rest_docs if rest_docs else np.full(len(terms), np.nan)
        rec.update({"z": z, "rest_share": rest_share})
    t = pd.DataFrame(rec)
    t["words"] = t["term"].str.count(" ") + 1
    t = t.sort_values(["docs", "occ", "term"], ascending=[False, False, True], kind="mergesort").reset_index(drop=True)
    t["rank"] = np.arange(1, len(t) + 1)
    if top_n:
        t = t[t["rank"] <= top_n]
    for _, r in t.iterrows():
        row = {**dict(zip(group_fields, gk if group_fields else ())), "Term": r["term"], "Words In Term": int(r["words"]), "Occurrences": int(r["occ"]),
               "Rows Using Term": int(r["docs"]), "Share Of Rows": float(r["share"]), "Rank": int(r["rank"])}
        if group_fields:
            row.update({"Share Of Rows In Other Groups": float(r["rest_share"]), "Distinctiveness (z)": float(r["z"]),
                        "Distinctive": "Yes" if r["z"] > 1.96 else "No"})
        rows.append(row)
cols = list(group_fields) + ["Term", "Words In Term", "Occurrences", "Rows Using Term", "Share Of Rows", "Rank"] + \
    (["Share Of Rows In Other Groups", "Distinctiveness (z)", "Distinctive"] if group_fields else [])
terms_df = pd.DataFrame(rows, columns=cols)
for c in ("Words In Term", "Occurrences", "Rows Using Term", "Rank"):
    terms_df[c] = terms_df[c].astype("int64")
for c in ("Share Of Rows", "Share Of Rows In Other Groups", "Distinctiveness (z)"):
    if c in terms_df:
        terms_df[c] = terms_df[c].astype("float64")

out = df.copy()
raw_words = [len(TOKEN.findall(str(t).lower())) if t is not None and not (isinstance(t, float) and t != t) else 0 for t in df[text_f].tolist()]
out["Word Count"] = pd.array(raw_words, dtype="int64")
out["Terms Kept"] = pd.array([len(t) for t in tok_lists], dtype="int64")
top_terms = set(terms_df[terms_df["Words In Term"] == 1].sort_values("Rows Using Term", ascending=False)["Term"].head(50)) if len(terms_df) else set()
out["Top Terms Used"] = ["; ".join(sorted(set(t) & top_terms)) or None for t in tok_lists]

omniscope_api.write_output(terms_df, "terms")
omniscope_api.write_output(out, "rows")
omniscope_api.close(f"{total_docs:,} rows, {sum(raw_words):,} words; {len(keep):,} distinct terms used in at least {min_docs} rows"
                    + (f"; {int((terms_df['Distinctive'] == 'Yes').sum()):,} distinctive term-group pairs" if group_fields else "") + ".")
