# Multi-Field Formula

Applies one operation (round, scale, share of row or column total, index to base, z-score, fill, text case...) to many fields chosen by list, name pattern or type, with optional row statistics.

One operation applied to many fields, for the common cases. Typical for wide tables such as one column per month.

**Choose the fields** explicitly, by a **name pattern** (a regular expression such as `2025$` or `^(Jan|Feb|Mar)`, so new columns are picked up automatically), or simply all number or text fields.

**Number operations**: round, multiply, divide, add, subtract, **share of row total** (each field as a share of the selected fields' row total), **share of column total**, **index to a base field** (base = 100) or difference from it, z-score, min-max scaling, log, absolute value, floor / cap at a value, fill missing with a value, convert text to numbers.

**Text operations**: upper, lower, title case, trim (and collapse spaces), add a prefix or suffix, fill missing text, length.

**Replace** the fields or **add new ones** with a suffix, and optionally add **row statistics** across the selected fields: sum, mean, minimum, maximum, count, standard deviation.

## Language
Python

## Inputs
- **Input 1**: data with the fields to transform (often one column per period).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Fields | Fields | `fields` | Fields | Leave empty to use a name pattern or all fields. From input 1. |
| Fields | Field name pattern (regular expression) | `field_pattern` | Text | Adds every field whose name matches, for example 2025$ for all 2025 columns. |
| Fields | Only fields of type | `type_filter` | Choice | Choices: Any type; Numbers; Text. Default: Any type. |
| Operation | Operation | `operation` | Choice | What to do to every chosen field. Choices: Round; Multiply by value; Divide by value; Add value; Subtract value; Share of row total; Share of column total; Index to base field (base = 100); Difference from base field; Z-score; Min-max scale (0 to 1); Natural log; Absolute value; Floor at value; Cap at value; Fill missing with value; Convert text to number; Text: UPPER; Text: lower; Text: Title Case; Text: trim spaces; Text: add prefix; Text: add suffix; Text: fill missing; Text: length; None (row statistics only). Default: Round. |
| Operation | Value | `value` | Decimal number | For multiply, divide, add, subtract, floor, cap and fill. Default: 0.0. |
| Operation | Decimal places (round) | `decimals` | Whole number | Default: 2. |
| Operation | Base field (index / difference) | `base_field` | Field | From input 1. |
| Operation | Text (prefix, suffix, fill) | `text_value` | Text |  |
| Output | Results | `output` | Choice | Overwrite the fields, or add new ones next to them. Choices: Replace the fields; Add new fields. Default: Replace the fields. |
| Output | Suffix for new fields | `suffix` | Text | Added to the name of each new field. Default:  (new). |
| Output | Row sum | `row_sum` | Tick box | Adds the total of the chosen fields for each row. Default: unticked. |
| Output | Row mean | `row_mean` | Tick box | Default: unticked. |
| Output | Row minimum | `row_min` | Tick box | Default: unticked. |
| Output | Row maximum | `row_max` | Tick box | Default: unticked. |
| Output | Row count of values | `row_count` | Tick box | Default: unticked. |
| Output | Row standard deviation | `row_std` | Tick box | Default: unticked. |

## Outputs
- **Output 1** (`Output Data`): The input with the operation applied (or new fields added) and any row statistics.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
