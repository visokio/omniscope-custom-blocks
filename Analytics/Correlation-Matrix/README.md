# Correlation Matrix

Pearson and Spearman correlations with p-values for all pairs of numeric fields or against a target, per group, ranked, with a heat-map matrix.

**Pearson and Spearman correlations with p-values** for every pair of numeric fields, or for each field against one **target**, overall and per **group**.

- Each pair uses all rows where both fields have values; pairs with fewer rows than the minimum are left blank
- Spearman (rank) correlation catches monotonic relationships that are not straight lines and is less affected by outliers
- **Strength** labels (negligible, weak, moderate, strong, very strong), direction and significance at your level
- Pairs are **ranked** by strength, so the strongest relationships come first

Outputs: one row per pair; the matrix in long form (row field, column field, correlation) for a heat map; and a wide matrix with one row per field. Correlation is not causation: use it to find relationships worth investigating.

## Language
Python

## Inputs
- **Input**: data with numeric fields.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | Numeric fields | `fields` | Fields | Leave empty to use every numeric field. From input 1. |
|  | Target (optional) | `target_field` | Field | Correlate every field with this one only. From input 1. |
|  | Per group (optional) | `group_field` | Field | From input 1. |
|  | Rank and label by | `method` | Choice | Choices: Pearson; Spearman (rank). Default: Pearson. |
|  | Significance level | `significance` | Decimal number | Default: 0.05. |
|  | Minimum rows per pair | `min_pairs` | Whole number | Default: 10. |

## Outputs
- **Pairs** (`pairs`): Per pair: rows, Pearson and Spearman with p-values, strength, direction, significant, rank.
- **Matrix (long)** (`matrix`): Row field, column field, correlation, p-value, rows: for heat maps.
- **Matrix (wide)** (`wide`): One row per field, one column per field.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the core Covariance Correlation block

Use the core **Covariance Correlation** block for a covariance or Pearson correlation matrix. Use this block when you need Spearman correlations, p-values, correlations per group, or every field against one target.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
