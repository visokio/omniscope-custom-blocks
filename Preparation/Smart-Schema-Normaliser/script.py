import re
import pandas as pd
from omniscope.api import OmniscopeApi

api = OmniscopeApi()

def opt(name, default):
    v = api.get_option(name)
    return default if v is None or str(v).strip() == "" else v

prefer_non_empty = str(opt("prefer_non_empty_strings", "true")).strip().lower() in ("true","1","yes","y")
sort_columns = str(opt("sort_columns", "true")).strip().lower() in ("true","1","yes","y")

try:
    threshold = float(opt("auto_cast_threshold", 0.98))
except Exception:
    threshold = 0.98

dt_default_raw = str(opt("datetime_default", "1970-01-01"))
num_default = float(opt("number_default", 0))
str_default = str(opt("string_default", ""))

dt_default = pd.to_datetime(dt_default_raw, errors="coerce")
if pd.isna(dt_default):
    dt_default = pd.Timestamp("1970-01-01")

def norm(name: str) -> str:
    s = "" if name is None else str(name).strip().lower()
    s = s.replace("-", "_")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s

def coalesce_cols(df: pd.DataFrame, cols: list) -> pd.Series:
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

def auto_cast(s: pd.Series) -> pd.Series:
    # number
    num = pd.to_numeric(s, errors="coerce")
    if num.notna().mean() >= threshold:
        return num.fillna(num_default)

    # datetime
    dt = pd.to_datetime(s, errors="coerce", infer_datetime_format=True, utc=False)
    if dt.notna().mean() >= threshold:
        return dt.fillna(dt_default)

    # boolean
    ss = s.astype("string").str.strip().str.lower()
    if ss.isin(["true","false","t","f","1","0","yes","no","y","n"]).mean() >= threshold:
        b = ss.isin(["true","t","1","yes","y"])
        return b.fillna(False)

    # string
    return s.astype("string").fillna(str_default)

def handle_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    groups = {}
    for c in chunk.columns:
        groups.setdefault(norm(c), []).append(c)

    out = pd.DataFrame(index=chunk.index)
    for new_name, cols in groups.items():
        series = coalesce_cols(chunk, cols) if len(cols) > 1 else chunk[cols[0]]
        out[new_name] = auto_cast(series)

    cols = list(out.columns)
    if sort_columns:
        cols = sorted(cols)
        out = out[cols]

    return out

api.process_stream(handle_chunk)
api.close()