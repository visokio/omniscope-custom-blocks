from omniscope.api import OmniscopeApi
import pandas as pd
import numpy as np
from pandas.api.types import is_integer_dtype  # <-- needed for median fill

api = OmniscopeApi()

# --- 0. Read block options ---
# Configure these as boolean options in the block UI: annotateData, findIssues, enrichData
annotate_data = bool(api.get_option("annotateData"))
find_issues = bool(api.get_option("findIssues"))
enrich_data = bool(api.get_option("enrichData"))

# --- 1. Read input data ---
df = api.read_input_records(input_number=0)

if df is None or df.empty:
    api.commit(message="No input data.")
    raise SystemExit()

# Work on a copy and create a stable row key
df = df.copy().reset_index(drop=True)
df["Row ID"] = df.index  # stable row identifier for joins / reporting

# If nothing is selected, just stop
if not (annotate_data or find_issues or enrich_data):
    api.commit(message="No operations selected.")
    raise SystemExit()

# --- 2. Prepare helpers for issue detection ---
issues_rows = []   # collect issue records here (long format)
row_flags = pd.Series("", index=df.index, name="Issue Flags")

def add_issue(mask, issue_type, column=None, details=None):
    """
    Record one issue row per (row, issue) in a compact issues table.
    Also append a code to the per-row Issue Flags field for annotated output.
    """
    if not mask.any():
        return

    # Update per-row flags (for Annotated output – quick human-readable view)
    code = issue_type if column is None else f"{issue_type}:{column}"
    row_flags.loc[mask] = (
        row_flags.loc[mask]
        .replace("", code)
        .where(row_flags.loc[mask] == "", row_flags.loc[mask] + "," + code)
    )

    # Build a compact issues table: one row per issue instance
    rows = df.index[mask]
    tmp = pd.DataFrame({
        "Row ID": rows,
        "Issue Type": issue_type,
        "Issue Column": column,
        "Issue Details": details,
    })
    issues_rows.append(tmp)

# --- 3. Detect issues only if needed (annotateData or findIssues) ---
numeric_cols = df.select_dtypes(include=[np.number]).columns
# Don't treat Row ID as a numeric field for quality checks
numeric_cols = [c for c in numeric_cols if c != "Row ID"]

if annotate_data or find_issues:
    # 3.1 Detect duplicates (full-row duplicates)
    dup_mask = df.drop(columns=["Row ID"]).duplicated(keep=False)  # exclude technical key
    add_issue(
        dup_mask,
        issue_type="DUPLICATE_ROW",
        column=None,
        details="Row is a duplicate of at least one other row (full-row duplicate).",
    )

    # 3.2 Detect missing values
    missing_mask = df.drop(columns=["Row ID"]).isna()
    for col in missing_mask.columns:
        col_mask = missing_mask[col]
        if col_mask.any():
            add_issue(
                col_mask,
                issue_type="MISSING VALUE",
                column=col,
                details="Value is null/NaN.",
            )

    # 3.3 Detect outliers in numeric columns (IQR-based)
    for col in numeric_cols:
        series = df[col].dropna()
        if series.empty:
            continue

        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            # No spread -> outlier detection not meaningful
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        out_mask = (df[col] < lower) | (df[col] > upper)

        if out_mask.any():
            details = (
                f"Value outside IQR bounds: [{lower:.4g}, {upper:.4g}] "
                f"(col='{col}')."
            )
            add_issue(
                out_mask,
                issue_type="OUTLIER",
                column=col,
                details=details,
            )

# --- 4. Build Issue log output (Output 1) if requested ---
issues_df = None
if find_issues:
    if issues_rows:
        issues_df = pd.concat(issues_rows, axis=0, ignore_index=True)
    else:
        # No issues: still output a simple table so downstream blocks don't break
        # Force Row ID to use the same (numeric) dtype as in df
        issues_df = pd.DataFrame({
            "Row ID": pd.Series(dtype=df["Row ID"].dtype),
            "Issue Type": pd.Series(dtype="object"),
            "Issue Column": pd.Series(dtype="object"),
            "Issue Details": pd.Series(dtype="object"),
        })
    api.write_output(issues_df, 1)

# --- 5. Build Annotated data output (Output 0) if requested ---
if annotate_data:
    annotated_df = df.copy()

    # Per-row human-readable flags
    annotated_df["Issue Flags"] = row_flags

    # Numeric summary: how many issues affect each row?
    issue_count = pd.Series(0, index=df.index, dtype=int)
    nonempty = row_flags != ""
    issue_count[nonempty] = row_flags[nonempty].str.count(",") + 1
    annotated_df["Issue Count"] = issue_count

    api.write_output(annotated_df, 0)

# --- 6. Enrich data (Output 2) if requested ---
if enrich_data:
    enriched_df = df.copy()

    # Fill numeric columns
    for col in numeric_cols:
        series = enriched_df[col]

        if not series.isna().any():
            continue

        median = series.median()

        # If all values are NaN, median will be NaN: nothing to fill
        if pd.isna(median):
            continue

        # If this is an integer-like dtype and median is non-integer,
        # upcast to a nullable float type first.
        if is_integer_dtype(series.dtype) and not float(median).is_integer():
            series = series.astype("Float64")
            enriched_df[col] = series.fillna(median)
        else:
            enriched_df[col] = series.fillna(median)

    # Fill categorical / object / bool columns
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns
    for col in cat_cols:
        series = enriched_df[col]
        if series.isna().any():
            try:
                mode = series.mode().iloc[0]
            except IndexError:
                # All values are NaN -> nothing sensible to fill with
                continue
            enriched_df[col] = series.fillna(mode)

    # Add a flag column showing which rows changed during enrichment
    changed_mask = (df.ne(enriched_df)) & ~(df.isna() & enriched_df.isna())
    enriched_df["_was_enriched"] = changed_mask.any(axis=1)

    api.write_output(enriched_df, 2)

# --- 7. Final message in the block bar ---
parts = []
if find_issues:
    if issues_rows:
        parts.append("issues detected")
    else:
        parts.append("no issues detected")
if annotate_data:
    parts.append("data annotated")
if enrich_data:
    parts.append("data enriched")

if parts:
    msg = " / ".join(parts).capitalize() + "."
else:
    msg = "Data passed through."

api.commit(message=msg)
