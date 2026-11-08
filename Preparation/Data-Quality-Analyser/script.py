"""Data Quality Analyser: finds duplicate records, missing values and numeric outliers.

Outputs (each only when its option is ticked):
  annotated - the input with Row ID, Issue Flags and Issue Count fields
  issues    - one record per issue found: Row ID, Issue Type, Issue Field, Issue Details
  enriched  - the input with missing numbers filled with the field's median and missing text with its mode,
              plus a Was Enriched field
"""
from omniscope.api import OmniscopeApi
import pandas as pd
from pandas.api.types import is_bool_dtype, is_integer_dtype, is_numeric_dtype, is_object_dtype, is_string_dtype

api = OmniscopeApi()

annotate_data = bool(api.get_option("annotateData"))
find_issues = bool(api.get_option("findIssues"))
enrich_data = bool(api.get_option("enrichData"))

df = api.read_input_records(input_number=0)
if df is None:
    api.abort("Connect a data source to the block's input.")

if not (annotate_data or find_issues or enrich_data):
    api.abort("Tick at least one output: annotated data, issue log or enriched data.")

df = df.reset_index(drop=True)
input_fields = list(df.columns)


def free_name(name, taken):
    """`name`, or `name 2`, `name 3`... if the input already has a field called `name`."""
    candidate, n = name, 2
    while candidate in taken:
        candidate, n = f"{name} {n}", n + 1
    return candidate


renamed = []


def added_field(name):
    chosen = free_name(name, set(input_fields) | set(added.values()))
    if chosen != name:
        renamed.append(f"{name} -> {chosen}")
    return chosen


added = {}
for name in ["Row ID", "Issue Flags", "Issue Count", "Was Enriched"]:
    added[name] = added_field(name)
ROW_ID, FLAGS, COUNT, ENRICHED = (added[k] for k in ["Row ID", "Issue Flags", "Issue Count", "Was Enriched"])

# Row ID is the record's position in the input, counting from 1; it links the three outputs
row_id = pd.Series(range(1, len(df) + 1), index=df.index, dtype="int64")


def is_text(dtype):
    return (is_object_dtype(dtype) or is_string_dtype(dtype)) and not is_bool_dtype(dtype)


numeric_fields = [c for c in input_fields if is_numeric_dtype(df[c].dtype) and not is_bool_dtype(df[c].dtype)]
text_fields = [c for c in input_fields if is_text(df[c].dtype)]

# --- Issue detection ---
issue_tables = []
flag_lists = [[] for _ in range(len(df))]


def add_issue(mask, issue_type, field, details):
    mask = pd.Series(mask, index=df.index).fillna(False).astype(bool)
    if not mask.any():
        return
    code = issue_type if field is None else f"{issue_type}:{field}"
    positions = mask.to_numpy().nonzero()[0]
    for p in positions:
        flag_lists[p].append(code)
    issue_tables.append(pd.DataFrame({
        ROW_ID: row_id.iloc[positions].to_numpy(),
        "Issue Type": issue_type,
        "Issue Field": field,
        "Issue Details": details,
    }))


if (annotate_data or find_issues) and len(df):
    add_issue(df.duplicated(keep=False), "DUPLICATE_ROW", None,
              "Every field is the same as in at least one other record.")

    for col in input_fields:
        add_issue(df[col].isna(), "MISSING_VALUE", col, "Value is missing.")

    for col in numeric_fields:
        values = df[col].astype("float64")
        present = values.dropna()
        if present.empty:
            continue
        q1, q3 = present.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue  # no spread: every value but the common one would be an outlier
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        add_issue((values < lower) | (values > upper), "OUTLIER", col,
                  f"Value outside the range {lower:.4g} to {upper:.4g} (1.5 times the interquartile range "
                  f"beyond the quartiles).")

issue_count = sum(len(f) for f in flag_lists)

if find_issues:
    if issue_tables:
        issues_df = pd.concat(issue_tables, ignore_index=True)
    else:
        issues_df = pd.DataFrame({
            ROW_ID: pd.Series(dtype="int64"),
            "Issue Type": pd.Series(dtype=object),
            "Issue Field": pd.Series(dtype=object),
            "Issue Details": pd.Series(dtype=object),
        })
    api.write_output(issues_df, "issues")

if annotate_data:
    annotated_df = df.copy()
    annotated_df.insert(0, ROW_ID, row_id)
    annotated_df[FLAGS] = pd.Series([",".join(f) for f in flag_lists], index=df.index, dtype=object)
    annotated_df[COUNT] = pd.Series([len(f) for f in flag_lists], index=df.index, dtype="int64")
    api.write_output(annotated_df, "annotated")

filled = 0
if enrich_data:
    enriched_df = df.copy()
    for col in numeric_fields:
        series = enriched_df[col]
        if not series.isna().any():
            continue
        median = series.astype("float64").median()
        if pd.isna(median):
            continue  # every value missing: nothing to take a median of
        if is_integer_dtype(series.dtype) and not float(median).is_integer():
            series = series.astype("float64")  # the median of whole numbers can be x.5
        enriched_df[col] = series.fillna(median)
    for col in text_fields:
        series = enriched_df[col]
        if not series.isna().any():
            continue
        modes = series.mode(dropna=True)
        if modes.empty:
            continue
        enriched_df[col] = series.fillna(modes.iloc[0])  # ties: the first value in sort order
    was_filled = df[input_fields].isna() & enriched_df[input_fields].notna()
    filled = int(was_filled.to_numpy().sum())
    enriched_df.insert(0, ROW_ID, row_id)
    enriched_df[ENRICHED] = was_filled.any(axis=1).astype(bool)
    api.write_output(enriched_df, "enriched")

parts = [f"{len(df):,} records checked"]
if annotate_data or find_issues:
    parts.append(f"{issue_count:,} issues found")
if enrich_data:
    parts.append(f"{filled:,} missing values filled")
if renamed:
    parts.append("fields renamed to avoid clashes with input fields: " + ", ".join(renamed))
api.commit(message="; ".join(parts) + ".")
