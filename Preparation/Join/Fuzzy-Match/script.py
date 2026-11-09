"""Fuzzy Match: find near-duplicate records within one input, or the best
matching record in a second (reference) input.

One input connected  -> de-duplicate mode: records that match each other are
                        given the same Group ID.
Two inputs connected -> lookup mode: every record of the first input gets its
                        best match(es) from the second input, with a score.

Pure Python / pandas: no extra packages needed.
"""
import re
import unicodedata
from collections import defaultdict

import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

# ----------------------------------------------------------------- options
match_field = omniscope_api.get_option("match_field")
reference_field = omniscope_api.get_option("reference_field")
second_field = omniscope_api.get_option("second_field")
second_reference_field = omniscope_api.get_option("second_reference_field")
second_weight = omniscope_api.get_option("second_weight")
block_field = omniscope_api.get_option("block_field")
block_reference_field = omniscope_api.get_option("block_reference_field")
algorithm = omniscope_api.get_option("algorithm") or "TOKEN_SORT_JW"
threshold = omniscope_api.get_option("threshold")
max_matches = omniscope_api.get_option("max_matches") or 1
normalise = omniscope_api.get_option("normalise")
ignore_suffixes = omniscope_api.get_option("ignore_suffixes")
ignore_words = omniscope_api.get_option("ignore_words") or ""

threshold = 0.85 if threshold is None else float(threshold)
second_weight = 0.3 if second_weight is None else float(second_weight)
max_matches = max(1, int(max_matches))

MAX_CANDIDATES = 60  # candidates scored per record after trigram pre-selection

COMPANY_SUFFIXES = {
    "ltd", "limited", "plc", "llc", "llp", "inc", "incorporated", "corp", "corporation", "co",
    "company", "gmbh", "ag", "sa", "sas", "sarl", "srl", "spa", "bv", "nv", "pty", "the", "lp",
}
EXTRA_IGNORED = {w.strip().lower() for w in re.split(r"[,;\n]", ignore_words) if w.strip()}

# ------------------------------------------------------------- similarity

def normalise_text(value):
    if value is None or (isinstance(value, float) and value != value):
        return ""
    s = str(value)
    if normalise:
        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
        s = s.replace("&", " and ")
        s = re.sub(r"[^\w\s]", " ", s)
    words = s.split()
    if ignore_suffixes:
        words = [w for w in words if w.lower() not in COMPANY_SUFFIXES]
    if EXTRA_IGNORED:
        words = [w for w in words if w.lower() not in EXTRA_IGNORED]
    return " ".join(words)


def levenshtein_ratio(a, b):
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return 1.0 - prev[-1] / max(len(a), len(b))


def jaro_winkler(a, b, p=0.1):
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if not la or not lb:
        return 0.0
    rng = max(la, lb) // 2 - 1
    am, bm = [False] * la, [False] * lb
    m = 0
    for i, ca in enumerate(a):
        lo, hi = max(0, i - rng), min(i + rng + 1, lb)
        for j in range(lo, hi):
            if not bm[j] and b[j] == ca:
                am[i] = bm[j] = True
                m += 1
                break
    if not m:
        return 0.0
    t, k = 0, 0
    for i in range(la):
        if am[i]:
            while not bm[k]:
                k += 1
            if a[i] != b[k]:
                t += 1
            k += 1
    jaro = (m / la + m / lb + (m - t / 2) / m) / 3
    prefix = 0
    for ca, cb in zip(a[:4], b[:4]):
        if ca != cb:
            break
        prefix += 1
    return jaro + prefix * p * (1 - jaro)


def trigrams(s):
    s = f"  {s} "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def trigram_similarity(a, b):
    if a == b:
        return 1.0
    ta, tb = trigrams(a), trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def token_set_ratio(a, b):
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    inter = " ".join(sorted(sa & sb))
    t1 = (inter + " " + " ".join(sorted(sa - sb))).strip()
    t2 = (inter + " " + " ".join(sorted(sb - sa))).strip()
    scores = [levenshtein_ratio(t1, t2)]
    if inter:
        scores += [levenshtein_ratio(inter, t1), levenshtein_ratio(inter, t2)]
    return max(scores)


def similarity(a, b):
    if not a or not b:
        return 0.0
    if algorithm == "JW":
        return jaro_winkler(a, b)
    if algorithm == "LEVENSHTEIN":
        return levenshtein_ratio(a, b)
    if algorithm == "TOKEN_SET":
        return token_set_ratio(a, b)
    if algorithm == "TRIGRAM":
        return trigram_similarity(a, b)
    # TOKEN_SORT_JW (default): word order does not matter, typos are tolerated
    return jaro_winkler(" ".join(sorted(a.split())), " ".join(sorted(b.split())))


# ------------------------------------------------------------------ data
left = omniscope_api.read_input_records(input_number=0)
right = omniscope_api.read_input_records(input_number=1)

if left is None:
    omniscope_api.abort("Connect the records to match to the first input.")
if not match_field:
    omniscope_api.abort("Choose the match field.")
if match_field not in left.columns:
    omniscope_api.abort(f"Match field '{match_field}' is not in the first input.")

lookup_mode = right is not None


def resolve(field_name, ref_name, label):
    """Field to use in the reference input: chosen one, else same name."""
    if not field_name:
        return None
    name = ref_name or field_name
    if name not in right.columns:
        omniscope_api.abort(f"{label} '{name}' is not in the second input; choose it in the options.")
    return name


if lookup_mode:
    ref_match = resolve(match_field, reference_field, "Match field")
    ref_second = resolve(second_field, second_reference_field, "Second field")
    ref_block = resolve(block_field, block_reference_field, "Exact match field")
for f, label in ((second_field, "Second field"), (block_field, "Exact match field")):
    if f and f not in left.columns:
        omniscope_api.abort(f"{label} '{f}' is not in the first input.")


def prepared(df, mfield, sfield, bfield):
    keys = [normalise_text(v) for v in df[mfield].tolist()]
    seconds = [normalise_text(v) for v in df[sfield].tolist()] if sfield else None
    blocks = [normalise_text(v) for v in df[bfield].tolist()] if bfield else None
    return keys, seconds, blocks


def score_pair(i, j, lk, ls, rk, rs):
    s = similarity(lk[i], rk[j])
    if ls is not None and rs is not None and ls[i] and rs[j]:
        s = (1 - second_weight) * s + second_weight * similarity(ls[i], rs[j])
    return s


class TrigramIndex:
    """Pre-selects plausible candidates so the block scales beyond a cross join."""

    def __init__(self, keys, blocks):
        self.index = defaultdict(list)
        self.blocks = blocks
        for j, k in enumerate(keys):
            if k:
                for g in trigrams(k):
                    self.index[g].append(j)
        n = max(1, len(keys))
        self.stop = {g for g, lst in self.index.items() if len(lst) > max(200, n * 0.05)}

    def candidates(self, key, block=None, exclude_upto=None):
        counts = defaultdict(int)
        grams = trigrams(key)
        for g in grams:
            if g in self.stop:
                continue
            for j in self.index.get(g, ()):
                counts[j] += 1
        if not counts:  # every trigram was a stop-gram: fall back to them
            for g in grams:
                for j in self.index.get(g, ()):
                    counts[j] += 1
        items = counts.items()
        if exclude_upto is not None:
            items = [(j, c) for j, c in items if j > exclude_upto]
        if self.blocks is not None:
            items = [(j, c) for j, c in items if self.blocks[j] == block]
        return [j for j, _ in sorted(items, key=lambda x: -x[1])[:MAX_CANDIDATES]]


def with_block_index(keys, blocks):
    """Exact blocking field: compare only within the same block value."""
    groups = defaultdict(list)
    for j, b in enumerate(blocks):
        if keys[j]:
            groups[b].append(j)
    return groups


omniscope_api.update_message("Preparing match keys...")
lk, ls, lb = prepared(left, match_field, second_field, block_field)

if lookup_mode:
    rk, rs, rb = prepared(right, ref_match, ref_second, ref_block)
    small_blocks = rb is not None and max((len(v) for v in with_block_index(rk, rb).values()), default=0) <= MAX_CANDIDATES
    idx = None if small_blocks else TrigramIndex(rk, rb)
    block_groups = with_block_index(rk, rb) if small_blocks else None
    rows, pairs = [], []
    for i in range(len(left)):
        if i % 2000 == 0:
            omniscope_api.update_message(f"Matching record {i + 1:,} of {len(left):,}")
        if not lk[i]:
            continue
        cands = block_groups.get(lb[i], []) if small_blocks else idx.candidates(lk[i], lb[i] if lb else None)
        scored = sorted(((score_pair(i, j, lk, ls, rk, rs), j) for j in cands), key=lambda x: (-x[0], x[1]))
        scored = [(s, j) for s, j in scored if s >= threshold][:max_matches]
        for rank, (s, j) in enumerate(scored, 1):
            pairs.append((i, j, rank, s))

    ref_cols = {c: f"Match: {c}" for c in right.columns}
    for c in list(ref_cols.values()):
        if c in left.columns:
            ref_cols = {k: (v + " (ref)" if v == c else v) for k, v in ref_cols.items()}
    by_left = defaultdict(list)
    for i, j, rank, s in pairs:
        by_left[i].append((j, rank, s))
    out_parts = []
    left_rows, ref_rows, scores, ranks, status = [], [], [], [], []
    for i in range(len(left)):
        found = by_left.get(i)
        if not found:
            left_rows.append(i)
            ref_rows.append(None)
            scores.append(float("nan"))
            ranks.append(pd.NA)
            status.append("No value" if not lk[i] else "No match")
        else:
            for j, rank, s in found:
                left_rows.append(i)
                ref_rows.append(j)
                scores.append(round(s, 4))
                ranks.append(rank)
                status.append("Matched")
    matched = left.iloc[left_rows].reset_index(drop=True)
    ref_part = right.reindex([r if r is not None else -1 for r in ref_rows]).reset_index(drop=True)
    ref_part = ref_part.rename(columns=ref_cols)
    matched = pd.concat([matched, ref_part], axis=1)
    matched["Match Score"] = pd.Series(scores, dtype="float64")
    matched["Match Rank"] = pd.array(ranks, dtype="Int64")
    matched["Match Status"] = status

    pair_df = pd.DataFrame({
        "Input Row": pd.array([i + 1 for i, _, _, _ in pairs], dtype="Int64"),
        "Reference Row": pd.array([j + 1 for _, j, _, _ in pairs], dtype="Int64"),
        "Input Value": [str(left[match_field].iloc[i]) for i, _, _, _ in pairs],
        "Reference Value": [str(right[ref_match].iloc[j]) for _, j, _, _ in pairs],
        "Score": pd.Series([round(s, 4) for _, _, _, s in pairs], dtype="float64"),
        "Rank": pd.array([r for _, _, r, _ in pairs], dtype="Int64"),
    })
    n_matched = len(by_left)
    summary = f"Lookup: {n_matched:,} of {len(left):,} records matched (threshold {threshold:g})."
else:
    # ---------------------------------------------------- de-duplicate mode
    n = len(left)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    pairs = []
    if lb is not None:
        groups = with_block_index(lk, lb)
        small = max((len(v) for v in groups.values()), default=0) <= MAX_CANDIDATES * 2
    else:
        small = False
    idx = None if small else TrigramIndex(lk, lb)
    for i in range(n):
        if i % 2000 == 0:
            omniscope_api.update_message(f"Comparing record {i + 1:,} of {n:,}")
        if not lk[i]:
            continue
        if small:
            cands = [j for j in groups.get(lb[i], []) if j > i]
        else:
            cands = idx.candidates(lk[i], lb[i] if lb else None, exclude_upto=i)
        for j in cands:
            s = score_pair(i, j, lk, ls, lk, ls)
            if s >= threshold:
                pairs.append((i, j, s))
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[max(ri, rj)] = min(ri, rj)

    roots = [find(i) for i in range(n)]
    gid, group_ids = {}, []
    for r in roots:
        if r not in gid:
            gid[r] = len(gid) + 1
        group_ids.append(gid[r])
    sizes = pd.Series(group_ids).map(pd.Series(group_ids).value_counts())
    best = [float("nan")] * n
    for i, j, s in pairs:
        best[i] = s if best[i] != best[i] else max(best[i], s)
        best[j] = s if best[j] != best[j] else max(best[j], s)
    matched = left.reset_index(drop=True).copy()
    matched["Group ID"] = pd.array(group_ids, dtype="Int64")
    matched["Group Size"] = pd.array(sizes.tolist(), dtype="Int64")
    matched["Is Group Master"] = ["Yes" if roots[i] == i else "No" for i in range(n)]
    matched["Best Match Score"] = pd.Series([round(b, 4) if b == b else b for b in best], dtype="float64")
    pair_df = pd.DataFrame({
        "Record 1": pd.array([i + 1 for i, _, _ in pairs], dtype="Int64"),
        "Record 2": pd.array([j + 1 for _, j, _ in pairs], dtype="Int64"),
        "Value 1": [str(left[match_field].iloc[i]) for i, _, _ in pairs],
        "Value 2": [str(left[match_field].iloc[j]) for _, j, _ in pairs],
        "Score": pd.Series([round(s, 4) for _, _, s in pairs], dtype="float64"),
        "Group ID": pd.array([group_ids[i] for i, _, _ in pairs], dtype="Int64"),
    })
    dup_groups = sum(1 for g, c in pd.Series(group_ids).value_counts().items() if c > 1)
    summary = f"De-duplicate: {n:,} records form {len(gid):,} groups; {dup_groups:,} groups have duplicates."

omniscope_api.write_output(matched, "matched")
omniscope_api.write_output(pair_df, "pairs")
omniscope_api.close(summary)
