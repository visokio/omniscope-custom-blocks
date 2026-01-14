import os
import re
import pandas as pd
from omniscope.api import OmniscopeApi

api = OmniscopeApi()

def opt(name, default=None):
    try:
        v = api.get_option(name)
        if v is None or str(v).strip() == "":
            return default
        return v
    except Exception:
        return default

# -------- Options --------
rules_path = opt("rules", "")
if not rules_path:
    api.abort("Option 'rules' must be a file path to a CSV rules file.")
if not os.path.exists(rules_path):
    api.abort(f"Rules file not found: {rules_path}")

prefer_non_empty = str(opt("prefer_non_empty_strings", "true")).strip().lower() in ("true","1","yes","y")
auto_normalise = str(opt("auto_normalise", "true")).strip().lower() in ("true","1","yes","y")
passthrough_unmapped = str(opt("passthrough_unmapped", "true")).strip().lower() in ("true","1","yes","y")

# -------- Helpers --------
def norm(name: str) -> str:
    s = "" if name is None else str(name).strip()
    if auto_normalise:
        s = s.lower()
        s = s.replace("-", "_")
        s = re.sub(r"\s+", "_", s)
        s = re.sub(r"_+", "_", s)
    return s

def split_aliases(raw: str):
    raw = "" if raw is None else str(raw)
    if "|" in raw:
        parts = [p.strip() for p in raw.split("|")]
    else:
        parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]

def coalesce_cols(df: pd.DataFrame, cols: list) -> pd.Series:
    if not cols:
        return pd.Series([pd.NA] * len(df), index=df.index)
    out = df[cols[0]]
    for c in cols[1:]:
        nxt = df[c]
        out = out.where(~out.isna(), nxt)
        if prefer_non_empty:
            try:
                mask_empty = out.astype("string").fillna("").str.len() == 0
                out = out.where(~mask_empty, nxt)
            except Exception:
                pass
    return out

def cast_and_fill(s: pd.Series, typ: str, default_val):
    typ = (typ or "string").strip().lower()

    if typ == "number":
        s = pd.to_numeric(s, errors="coerce")
        fill = 0 if default_val in (None, "") else float(default_val)
        return s.fillna(fill)

    if typ == "boolean":
        ss = s.astype("string").str.strip().str.lower()
        b = ss.isin(["true","t","1","yes","y"])
        return b.fillna(False)

    if typ in ("date", "datetime"):
        dt = pd.to_datetime(s, errors="coerce", infer_datetime_format=True, utc=False)
        fill_raw = default_val if default_val not in (None, "") else "1970-01-01"
        fill_dt = pd.to_datetime(fill_raw, errors="coerce")
        if pd.isna(fill_dt):
            fill_dt = pd.Timestamp("1970-01-01")
        dt = dt.fillna(fill_dt)
        if typ == "date":
            d = dt.dt.date
            return d.fillna(fill_dt.date())
        return dt

    # string
    s = s.astype("string")
    fill = "" if default_val in (None, "") else str(default_val)
    return s.fillna(fill)

# -------- Load rules once (startup) --------
rules = pd.read_csv(rules_path)

required_cols = {"canonical", "aliases"}
missing = required_cols - set(rules.columns)
if missing:
    api.abort(f"Rules CSV missing required columns: {sorted(missing)}")

if "type" not in rules.columns:
    rules["type"] = "string"
if "default" not in rules.columns:
    rules["default"] = ""

canon_defs = []
for _, r in rules.iterrows():
    canonical = str(r["canonical"]).strip()
    if not canonical:
        continue
    aliases = split_aliases(r["aliases"])
    aliases_norm = [norm(canonical)] + [norm(a) for a in aliases if a]
    canon_defs.append({
        "canonical": canonical,
        "type": str(r.get("type", "string")).strip().lower(),
        "default": r.get("default", ""),
        "aliases_norm": aliases_norm
    })

if not canon_defs:
    api.abort("Rules CSV produced no canonical fields (check 'canonical' values).")

# Track which canonical fields are actually used across chunks
active_canonical_cols = []
output_cols = None

def handle_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    global output_cols, active_canonical_cols

    # Build normalized input col lookup
    in_norm_to_actual = {}
    for c in chunk.columns:
        in_norm_to_actual.setdefault(norm(c), []).append(c)

    out = pd.DataFrame(index=chunk.index)
    used_input_cols = set()

    # Create canonical fields ONLY if at least one alias matches input data
    for d in canon_defs:
        src_cols = []
        for a_norm in d["aliases_norm"]:
            cols = in_norm_to_actual.get(a_norm, [])
            src_cols.extend(cols)
        
        # Only create this canonical field if we found matching input columns
        if src_cols:
            for c in src_cols:
                used_input_cols.add(c)
            
            s = coalesce_cols(chunk, src_cols)
            out[d["canonical"]] = cast_and_fill(s, d["type"], d["default"])
            
            # Track this canonical field as active for first chunk
            if output_cols is None and d["canonical"] not in active_canonical_cols:
                active_canonical_cols.append(d["canonical"])

    # Pass through any unmapped input fields
    if passthrough_unmapped:
        for c in chunk.columns:
            if c not in used_input_cols and c not in out.columns:
                out[c] = chunk[c]

    # Lock output schema/order based on first chunk
    if output_cols is None:
        output_cols = list(out.columns)

    # Enforce consistent schema/order for every chunk
    for c in output_cols:
        if c not in out.columns:
            out[c] = ""

    out = out[output_cols]
    return out

api.process_stream(handle_chunk)
api.close()
