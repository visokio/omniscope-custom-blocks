import csv
import os
import re

import pandas as pd
from omniscope.api import OmniscopeApi

api = OmniscopeApi()


def flag(name, default):
    """A checkbox option; unset (None) means the default."""
    v = api.get_option(name)
    if v is None or str(v).strip() == "":
        return default
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes", "y")


# -------- Options --------
# The rules come from the "Schema rules" text option when it is filled in (a rules CSV typed into the block),
# otherwise from the rules file option. A streaming block has exactly one input, so the rules can't arrive as a
# second, rules-table input.
rules_text = api.get_option("rulesText")
rules_text = str(rules_text) if rules_text is not None else ""
rules_path = api.get_option("rules")
rules_path = str(rules_path).strip() if rules_path is not None else ""
if not rules_text.strip():
    if not rules_path:
        api.abort("Write the rules in the Schema rules option, or choose a schema rules file.")
    if not os.path.exists(rules_path):
        api.abort(f"Schema rules file not found: {rules_path}")
RULES_SOURCE = "the Schema rules option" if rules_text.strip() else "the schema rules file"

passthrough_unmapped = flag("passthrough_unmapped", True)
prefer_non_empty = flag("prefer_non_empty_strings", True)
auto_normalise = flag("auto_normalise_aliases", True)
add_missing = flag("add_missing_canonical", False)

TYPES = {
    "string": "string", "text": "string", "": "string",
    "number": "number", "decimal": "number",
    "integer": "integer",
    "date": "date", "datetime": "datetime",
    "boolean": "boolean",
}
TRUE_WORDS = {"true", "t", "1", "yes", "y"}
FALSE_WORDS = {"false", "f", "0", "no", "n"}


# -------- Helpers --------
def norm(name) -> str:
    s = "" if name is None else str(name).strip()
    if auto_normalise:
        s = s.lower()
        s = s.replace("-", "_")
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"_+", "_", s)
    return s


def split_aliases(raw):
    raw = "" if raw is None else str(raw)
    parts = raw.split("|") if "|" in raw else raw.split(",")
    return [p.strip() for p in parts if p.strip()]


def blank(s: pd.Series) -> pd.Series:
    """True where a value is missing, or (with 'Treat blank text as missing') text that is empty or only spaces."""
    m = s.isna()
    if prefer_non_empty and (pd.api.types.is_object_dtype(s.dtype) or pd.api.types.is_string_dtype(s.dtype)):
        m = m | s.astype("string").str.strip().fillna("").eq("")
    return m.fillna(True).astype(bool)


def to_utc(s: pd.Series, fmt) -> pd.Series:
    """Parse to UTC dates. Date fields keep their instant; text is parsed with the rule's format, or ISO/mixed."""
    if pd.api.types.is_datetime64_any_dtype(s.dtype):
        return s.dt.tz_localize("UTC") if s.dt.tz is None else s.dt.tz_convert("UTC")
    txt = s.astype("string").str.strip()
    if fmt:
        # The rule's format first; values in ISO form (2025-01-31) are read too, as they are unambiguous
        out = pd.to_datetime(txt, errors="coerce", format=fmt, utc=True)
        return out.where(out.notna(), pd.to_datetime(txt, errors="coerce", format="ISO8601", utc=True))
    return pd.to_datetime(txt, errors="coerce", format="mixed", utc=True)


def convert(s: pd.Series, typ: str, fmt):
    """Convert a coalesced Series to the canonical type. Unreadable values become missing."""
    if typ in ("number", "integer"):
        if pd.api.types.is_bool_dtype(s.dtype):
            s = s.astype("float64")
        out = pd.to_numeric(s, errors="coerce").astype("float64")
        if typ == "integer":
            out = out.where(out.isna() | (out == out.round()))
            return out.astype("Int64")
        return out
    if typ == "boolean":
        if pd.api.types.is_bool_dtype(s.dtype):
            return s.astype("boolean")
        if pd.api.types.is_numeric_dtype(s.dtype):
            n = s.astype("float64")
            return n.map({1.0: True, 0.0: False}).astype("boolean")
        t = s.astype("string").str.strip().str.lower()
        out = pd.Series(pd.NA, index=s.index, dtype="boolean")
        out[t.isin(TRUE_WORDS).fillna(False).astype(bool)] = True
        out[t.isin(FALSE_WORDS).fillna(False).astype(bool)] = False
        return out
    if typ in ("date", "datetime"):
        dt = to_utc(s, fmt)
        return dt.dt.normalize() if typ == "date" else dt
    out = s.astype("string")
    if prefer_non_empty:
        out = out.where(~blank(s))
    return out


def typed_default(d, length, index):
    """A Series holding the rule's default (or missing), in the canonical type."""
    raw = pd.Series([d["default"] if d["default"] != "" else None] * length, index=index, dtype=object)
    return convert(raw, d["type"], None)  # defaults are written as ISO dates (2025-01-31), whatever the format


def fill_default(s: pd.Series, d) -> pd.Series:
    if d["default"] == "":
        return s
    return s.where(s.notna(), typed_default(d, len(s), s.index))


# -------- Load rules once (startup) --------
COLUMNS = ["canonical", "aliases", "type", "default", "format"]


def split_rows(text):
    """Rows of the typed rules: one per line, or separated by semicolons (outside double quotes)."""
    rows, cur, quoted = [], [], False
    for ch in text.replace("\r", "\n"):
        if ch == '"':
            quoted = not quoted
        if ch in "\n;" and not quoted:
            rows.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    rows.append("".join(cur))
    return [r for r in rows if r.strip()]


def rules_from_text(text):
    """The typed rules as a table of text. The heading row is optional: without one, the columns are
    canonical, aliases, type, default, format, in that order."""
    rows = [[c.strip() for c in r] for r in csv.reader(split_rows(text), skipinitialspace=True)]
    if rows and "canonical" in [c.lower() for c in rows[0]]:
        header, rows = rows[0], rows[1:]
    else:
        width = max(len(r) for r in rows)
        if width > len(COLUMNS):
            api.abort(f"A rule in the Schema rules option has {width} cells; a rule has at most five: "
                      "canonical, aliases, type, default, format.")
        header = COLUMNS[:max(width, 2)]
    rows = [(r + [""] * len(header))[:len(header)] for r in rows]
    return pd.DataFrame(rows, columns=header, dtype=object)


if rules_text.strip():
    rules = rules_from_text(rules_text)
else:
    try:
        rules = pd.read_csv(rules_path, dtype=str, keep_default_na=False, skipinitialspace=True,
                            encoding="utf-8-sig")
    except Exception as e:  # noqa: BLE001 - report any reading problem to the user
        api.abort(f"Could not read the schema rules file {rules_path}: {e}")

rules.columns = [str(c).strip().lower() for c in rules.columns]
missing_cols = {"canonical", "aliases"} - set(rules.columns)
if missing_cols:
    api.abort(f"The rules in {RULES_SOURCE} have no {' or '.join(sorted(missing_cols))} column. "
              "They need the columns canonical and aliases, and optionally type, default and format.")
for col in ("type", "default", "format"):
    if col not in rules.columns:
        rules[col] = ""

canon_defs = []
seen = set()
for _, r in rules.iterrows():
    canonical = str(r["canonical"]).strip()
    if not canonical:
        continue
    if canonical in seen:
        api.abort(f"The rules list the canonical field '{canonical}' twice.")
    seen.add(canonical)
    typ = str(r["type"]).strip().lower()
    if typ not in TYPES:
        api.abort(f"Unknown type '{r['type']}' for '{canonical}'. "
                  "Use string, number, integer, date, datetime or boolean.")
    aliases_norm = []
    for a in [canonical] + split_aliases(r["aliases"]):
        if norm(a) not in aliases_norm:
            aliases_norm.append(norm(a))
    d = {"canonical": canonical, "type": TYPES[typ], "default": str(r["default"]).strip(),
         "format": str(r["format"]).strip() or None, "aliases_norm": aliases_norm}
    if d["default"] != "" and typed_default(d, 1, pd.RangeIndex(1)).isna().all():
        api.abort(f"The default '{d['default']}' for '{canonical}' is not a valid {d['type']}.")
    canon_defs.append(d)

if not canon_defs:
    api.abort(f"The rules in {RULES_SOURCE} have no canonical field names (the canonical column is empty).")

output_cols = None
unreadable = {}  # canonical field -> count of values that could not be converted to its type


def handle_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    global output_cols

    in_norm_to_actual = {}
    for c in chunk.columns:
        in_norm_to_actual.setdefault(norm(c), []).append(c)

    input_col_to_canonical = {}
    canonical_data = {}
    for d in canon_defs:
        src_cols = []
        for a_norm in d["aliases_norm"]:
            for c in in_norm_to_actual.get(a_norm, []):
                if c not in src_cols:
                    src_cols.append(c)
        if not src_cols:
            if add_missing:
                canonical_data[d["canonical"]] = typed_default(d, len(chunk), chunk.index)
            continue
        # Convert each source field, then take the first usable value, in alias order
        value = None
        for c in src_cols:
            input_col_to_canonical.setdefault(c, d["canonical"])
            conv = convert(chunk[c], d["type"], d["format"])
            bad = int((conv.isna() & ~blank(chunk[c])).sum())
            if bad:
                unreadable[d["canonical"]] = unreadable.get(d["canonical"], 0) + bad
            value = conv if value is None else value.where(value.notna(), conv)
        canonical_data[d["canonical"]] = fill_default(value, d)

    out = pd.DataFrame(index=chunk.index)
    if add_missing:
        # Fixed schema: every canonical field in the rules' order, then the unmapped fields
        for d in canon_defs:
            out[d["canonical"]] = canonical_data[d["canonical"]]
        if passthrough_unmapped:
            for c in chunk.columns:
                if c not in input_col_to_canonical and c not in out.columns:
                    out[c] = chunk[c]
    else:
        # Input order: each canonical field takes the place of its first matching input field
        for c in chunk.columns:
            if c in input_col_to_canonical:
                canon = input_col_to_canonical[c]
                if canon not in out.columns:
                    out[canon] = canonical_data[canon]
            elif passthrough_unmapped and c not in out.columns:
                out[c] = chunk[c]

    if output_cols is None:
        output_cols = list(out.columns)
        mapped = [c for c in output_cols if c in seen]
        unmapped = [c for c in output_cols if c not in seen]
        parts = []
        if mapped:
            parts.append(f"Mapped {len(mapped)} canonical field(s): {', '.join(mapped)}")
        if unmapped:
            parts.append(f"Passed through {len(unmapped)} unmapped field(s): {', '.join(unmapped)}")
        if not parts:
            parts.append("No fields matched the schema rules")
        api.update_message(" | ".join(parts))
    elif list(out.columns) != output_cols:
        out = out.reindex(columns=output_cols)

    if unreadable:
        api.update_message("Values that could not be converted (now empty): "
                           + ", ".join(f"{k} {v}" for k, v in unreadable.items()))
    return out


# Each chunk is mapped with the same rules, and every canonical field always has the same type, so the output
# schema is the same on every chunk.
api.process_stream(handle_chunk)

# The data stream is over: no more data can be read or written.
api.close()
