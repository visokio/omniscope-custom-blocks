from omniscope.api import OmniscopeApi
import pandas as pd
import numpy as np

api = OmniscopeApi()

# --- 1. Read input data ---
df = api.read_input_records(input_number=0)

if df is None or df.empty:
    api.commit(message="No input data.")
    raise SystemExit()

# Work on a copy to avoid surprises
df = df.copy()

# --- 2. Prepare helpers ---
issues_rows = []   # collect issue records here
row_flags = pd.Series("", index=df.index, name="_issue_flags")

def add_issue(mask, issue_type, column=None, details=None):
    """
    Add one issue row per record where mask is True.
    Also append a code to the per-row _issue_flags field.
    """
    if not mask.any():
        return

    # Append short code to row flags (comma separated)
    code = issue_type if column is None else f"{issue_type}:{column}"
    row_flags.loc[mask] = (
        row_flags.loc[mask]
        .replace("", code)
        .where(row_flags.loc[mask] == "", row_flags.loc[mask] + "," + code)
    )

    # Build issue rows: one per offending record
    tmp = df.loc[mask].copy()
    tmp["Issue Type"] = issue_type
    tmp["Issue Column"] = column
    tmp["Issue Details"] = details
    issues_rows.append(tmp)


# --- 3. Detect duplicates (full-row duplicates) ---
dup_mask = df.duplicated(keep=False)  # mark all members of duplicate groups
add_issue(
    dup_mask,
    issue_type="DUPLICATE_ROW",
    column=None,
    details="Row is a duplicate of at least one other row (full-row duplicate).",
)

# --- 4. Detect missing values ---
missing_mask = df.isna()
for col in df.columns:
    col_mask = missing_mask[col]
    if col_mask.any():
        add_issue(
            col_mask,
            issue_type="MISSING_VALUE",
            column=col,
            details="Value is null/NaN.",
        )

# --- 5. Detect outliers in numeric columns (IQR-based) ---
numeric_cols = df.select_dtypes(include=[np.number]).columns

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

# --- 6. Build Issue log output (Output: 'issues') ---
if issues_rows:
    issues_df = pd.concat(issues_rows, axis=0, ignore_index=True)
else:
    # No issues: still output a simple table so downstream blocks don't break
    issues_df = pd.DataFrame(
        columns=list(df.columns) + ["_issue_type", "_issue_column", "_issue_details"]
    )

# --- 7. Build Annotated data output (Output: 'annotated') ---
annotated_df = df.copy()
annotated_df["_issue_flags"] = row_flags

# --- 8. Enrich data (simple automated enrichment) ---
#     - Fill numeric NaNs with median
#     - Fill text/categorical NaNs with mode (most frequent)

enriched_df = df.copy()

# Fill numeric columns
for col in numeric_cols:
    series = df[col]
    if series.isna().any():
        median = series.median()
        enriched_df[col] = series.fillna(median)

# Fill categorical / object / bool columns
cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns
for col in cat_cols:
    series = df[col]
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

# --- 9. Write outputs ---
# Make sure the output IDs match those configured in your block design.
api.write_output(annotated_df, 0)   # Output 1: data + _issue_flags
api.write_output(issues_df, 1)         # Output 2: detailed issues log
api.write_output(enriched_df, 2)     # Output 3: enriched data

# Final message in the block bar
msg = "Data verified and enriched."
if issues_df.empty:
    msg = "No issues detected. Enrichment still applied."

api.commit(message=msg)