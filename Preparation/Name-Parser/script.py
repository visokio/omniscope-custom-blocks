"""Name Parser: split full names into title, first name, middle names, last
name and suffix, and build salutations, for mailings and matching.

Handles "Dr Amelia J. Smith-Jones", "SMITH, AMELIA", "mr o'brien", initials,
surname particles (van, de, du, von, al...), suffixes (Jr, Sr, III, OBE, PhD...),
and flags values that look like organisations (Ltd, plc, LLP, Trust...).
Optionally tidies capitalisation (McDonald, O'Brien, Smith-Jones, van der Berg).
"""
import re

import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def opt(name, default=None):
    v = omniscope_api.get_option(name)
    return default if v is None or v == "" else v


name_f = opt("name_field")
fix_case = bool(opt("fix_case", True))
greeting = opt("greeting", "Dear")
style = opt("salutation_style", "FORMAL")
prefix = opt("prefix", "")

df = omniscope_api.read_input_records(input_number=0)
if df is None:
    omniscope_api.abort("Connect the data to the input.")
if not name_f or name_f not in df.columns:
    omniscope_api.abort(f"Choose the name field (got '{name_f}').")

TITLES = {"mr": "Mr", "mrs": "Mrs", "ms": "Ms", "miss": "Miss", "mx": "Mx", "dr": "Dr", "doctor": "Dr", "prof": "Prof", "professor": "Prof",
          "sir": "Sir", "dame": "Dame", "lord": "Lord", "lady": "Lady", "rev": "Rev", "revd": "Revd", "reverend": "Rev", "fr": "Fr", "capt": "Capt",
          "captain": "Capt", "col": "Col", "major": "Major", "maj": "Major", "cllr": "Cllr", "hon": "Hon", "rt hon": "Rt Hon", "sr": None}
SUFFIXES = {"jr": "Jr", "jnr": "Jnr", "junior": "Jr", "sr": "Sr", "snr": "Snr", "senior": "Sr", "ii": "II", "iii": "III", "iv": "IV",
            "obe": "OBE", "mbe": "MBE", "cbe": "CBE", "kbe": "KBE", "dbe": "DBE", "phd": "PhD", "md": "MD", "qc": "QC", "kc": "KC", "mp": "MP",
            "frcs": "FRCS", "bsc": "BSc", "msc": "MSc", "ma": "MA", "ba": "BA", "esq": "Esq", "cpa": "CPA", "aca": "ACA", "fca": "FCA"}
PARTICLES = {"van", "von", "der", "den", "de", "del", "della", "di", "da", "du", "le", "la", "st", "st.", "al", "el", "bin", "ibn", "ap", "ter", "dos", "das"}
ORG = re.compile(r"\b(ltd|limited|plc|llp|llc|inc|incorporated|corp|corporation|company|co\.|group|holdings|trust|council|services|partners|"
                 r"associates|foundation|society|university|school|church|club|bank|gmbh|s\.a\.|sarl|bv|nv|pty)\b|&", re.I)


def tidy_word(wd, first=False):
    if not fix_case or not wd:
        return wd
    lw = wd.lower()
    if lw in PARTICLES and not first:
        return lw
    if lw.upper() in ("II", "III", "IV"):
        return lw.upper()

    def cap(part):
        if not part:
            return part
        p = part.lower()
        if p.startswith("mc") and len(p) > 2:
            return "Mc" + p[2].upper() + p[3:]
        if p.startswith("o'") and len(p) > 2:
            return "O'" + p[2].upper() + p[3:]
        if p.startswith("d'") and len(p) > 2:
            return "D'" + p[2].upper() + p[3:]
        return p[0].upper() + p[1:]
    return "-".join(cap(x) for x in wd.split("-"))


def key(t):
    return t.lower().strip(".,")


def parse(raw):
    if raw is None or (isinstance(raw, float) and raw != raw) or str(raw).strip() == "":
        return dict(kind="Empty")
    s = re.sub(r"\s+", " ", str(raw).strip())
    if ORG.search(s):
        return dict(kind="Organisation", last=s)
    note = []
    comma_order = False
    if "," in s:
        head, tail = [x.strip() for x in s.split(",", 1)]
        tail_tokens = tail.split()
        if tail_tokens and all(key(t) in SUFFIXES for t in tail_tokens):
            s = head + " " + tail  # "John Smith, Jr"
        else:
            s = tail + " " + head
            comma_order = True
    tokens = s.split(" ")
    title = []
    while tokens:
        k2 = (key(tokens[0]) + " " + key(tokens[1])) if len(tokens) > 1 else None
        if k2 in TITLES:
            title.append(TITLES[k2]); tokens = tokens[2:]; continue
        if key(tokens[0]) in TITLES and TITLES[key(tokens[0])] and len(tokens) > 1:
            title.append(TITLES[key(tokens[0])]); tokens = tokens[1:]; continue
        break
    suffix = []
    if comma_order:
        # "Smith Jr, John" -> suffix sits before the comma part, now at the end
        pass
    while len(tokens) > 1 and key(tokens[-1]) in SUFFIXES:
        suffix.insert(0, SUFFIXES[key(tokens[-1])]); tokens = tokens[:-1]
    if not tokens:
        return dict(kind="Person", title=" ".join(title), suffix=" ".join(suffix), note="No name after the title")
    if len(tokens) == 1:
        t = tokens[0]
        if title:
            return dict(kind="Person", title=" ".join(title), last=tidy_word(t, True), suffix=" ".join(suffix), note="Title and surname only")
        return dict(kind="Person", first=tidy_word(t, True), suffix=" ".join(suffix), note="Single word")
    # surname = last token plus any particles before it
    i = len(tokens) - 1
    while i - 1 > 0 and key(tokens[i - 1]) in PARTICLES:
        i -= 1
    first = tokens[0]
    middle = tokens[1:i]
    last = tokens[i:]
    first_t = tidy_word(first, True)
    initials_only = re.fullmatch(r"[A-Za-z]\.?|([A-Za-z]\.){2,}", first) is not None
    if initials_only:
        note.append("First name is an initial")
    out = dict(kind="Person", title=" ".join(title), first=first_t.replace(".", "") if initials_only else first_t,
               middle=" ".join(tidy_word(m).replace(".", "") if len(m.strip(".")) == 1 else tidy_word(m) for m in middle),
               last=" ".join(tidy_word(x, key(x) not in PARTICLES) for x in last), suffix=" ".join(suffix), note="; ".join(note) or None,
               initial_first=initials_only)
    if comma_order:
        out["note"] = ((out["note"] + "; ") if out["note"] else "") + "Written as Last, First"
    return out


parsed = [parse(v) for v in df[name_f].tolist()]
out = df.copy()


def col(k):
    return [p.get(k) or None for p in parsed]


out[f"{prefix}Name Type"] = [p["kind"] for p in parsed]
out[f"{prefix}Title"] = col("title")
out[f"{prefix}First Name"] = col("first")
out[f"{prefix}Middle Names"] = col("middle")
out[f"{prefix}Last Name"] = col("last")
out[f"{prefix}Suffix"] = col("suffix")
inits = []
sal, full = [], []
for p in parsed:
    names = [x for x in (p.get("first"), *(p.get("middle") or "").split(), p.get("last")) if x]
    inits.append(("".join(x[0].upper() for x in names if x[0].isalpha()) or None) if p["kind"] == "Person" else None)
    fn = " ".join(x for x in (p.get("title"), p.get("first"), p.get("middle"), p.get("last"), p.get("suffix")) if x) or None
    full.append(fn if p["kind"] == "Person" else (p.get("last") if p["kind"] == "Organisation" else None))
    if p["kind"] != "Person":
        sal.append(f"{greeting} Sir or Madam" if p["kind"] == "Organisation" else None)
    elif p.get("title") and re.search(r"\b(Sir|Dame)\b", p["title"]) and p.get("first") and not p.get("initial_first"):
        sal.append(f"{greeting} {'Sir' if 'Sir' in p['title'] else 'Dame'} {p['first']}")  # knights and dames: Sir Robert, Dame Judi
    elif style == "INFORMAL" and p.get("first") and not p.get("initial_first"):
        sal.append(f"{greeting} {p['first']}")
    elif p.get("title") and p.get("last"):
        sal.append(f"{greeting} {p['title']} {p['last']}")
    elif p.get("first") and p.get("last") and not p.get("initial_first"):
        sal.append(f"{greeting} {p['first']} {p['last']}")
    elif p.get("last"):
        sal.append(f"{greeting} {(p.get('first') + ' ') if p.get('first') else ''}{p['last']}")
    else:
        sal.append(f"{greeting} {p.get('first')}" if p.get("first") else None)
out[f"{prefix}Initials"] = inits
out[f"{prefix}Tidy Name"] = full
out[f"{prefix}Salutation"] = sal
out[f"{prefix}Parse Note"] = col("note")
omniscope_api.write_output(out, "parsed")
kinds = pd.Series([p["kind"] for p in parsed]).value_counts()
omniscope_api.close(f"{len(out):,} names: {int(kinds.get('Person', 0)):,} people, {int(kinds.get('Organisation', 0)):,} organisations, {int(kinds.get('Empty', 0)):,} empty; "
                    f"{sum(1 for p in parsed if p.get('note')):,} with a note.")
