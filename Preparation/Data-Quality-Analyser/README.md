# Data Quality Analyser

Finds duplicate records, missing values and numeric outliers, and outputs an issue log, the data annotated with its issues, and a copy with missing values filled.

It checks every record of the input for three kinds of issue:

- **Duplicate records**: every field is the same as in at least one other record. All the copies are flagged, not just the second.
- **Missing values**: an empty value in any field (text, number, date or yes/no).
- **Outliers**: in each numeric field, a value more than 1.5 times the interquartile range below the first quartile or above the third (Tukey's fences). A field whose quartiles are equal is skipped.

Every output starts with a **Row ID**: the record's position in the input, counting from 1. It links the issue log to the annotated and enriched data.

## Language and libraries
Python, using pandas (part of Omniscope's Python environment). Nothing else to install.

## Inputs
- **Input 1**: any records.

## Options

| Option | Name in script | Type | Default | Description |
|---|---|---|---|---|
| Output annotated data | `annotateData` | Yes/no | Ticked | The input with a Row ID, the issues found in each record (Issue Flags) and how many there are (Issue Count). |
| Output issue log | `findIssues` | Yes/no | Ticked | One record per issue found: Row ID, Issue Type, Issue Field and Issue Details. |
| Output enriched data | `enrichData` | Yes/no | Not ticked | The input with missing numbers filled with the field's median and missing text with its most common value, and a Was Enriched field. |

At least one must be ticked.

## Outputs

- **Annotated** (`annotated`): Row ID, the input's fields, then
  - **Issue Flags**: the record's issues, comma-separated, such as `MISSING_VALUE:Branch,OUTLIER:Units`; empty when there are none;
  - **Issue Count**: how many issues the record has.
- **Issues** (`issues`): one record per issue:
  - **Row ID**;
  - **Issue Type**: `DUPLICATE_ROW`, `MISSING_VALUE` or `OUTLIER`;
  - **Issue Field**: the field concerned (empty for duplicates);
  - **Issue Details**: a description; for outliers, the range a value had to fall within.
- **Enriched** (`enriched`): Row ID, the input's fields with gaps filled, then **Was Enriched** (true for a record that had at least one value filled).

An output whose option is not ticked is left empty. With an empty input, each ticked output is empty but has its fields.

## How values are filled

- **Numbers**: the median of the field's values. If an integer field's median falls between two whole numbers (for example 2.5), the field becomes a decimal field.
- **Text**: the most common value; on a tie, the first in alphabetical order.
- **Dates and yes/no fields** are not filled.
- A field with no values at all is left empty.

The fill is a simple, whole-field one. For other methods (mean, constant, previous value, interpolation, within groups) use the community **Imputation** block.

## Field names
If the input already has a field called Row ID, Issue Flags, Issue Count or Was Enriched, the block's field gets a number instead (`Row ID 2`), and the block's message says so.

## Limits
- Outliers use one fixed rule (1.5 × IQR) over the whole field, not within groups. For other rules, groups or capping, use the community **Outlier Flagger** block.
- Duplicates compare every field; records that differ only in letter case are not duplicates.
- In tests (outside Omniscope), 200,000 records with 800,000 issues between them took under a second; the issue log has one record per issue, so it can be several times the size of the input.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
