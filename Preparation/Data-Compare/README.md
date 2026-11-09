# Data Compare

Compares two versions of a dataset by key: added, removed and changed records, field-level differences with tolerances, and schema differences.

Compares two versions of a dataset (before and after a migration, source and target, last month's extract and this month's) and shows exactly what changed.

- Records are matched on **key fields** (for example Customer ID); without keys, whole rows are matched
- Each record is **Added**, **Removed**, **Changed** or **Unchanged**, with the list of changed fields
- One row per **changed value** with old and new value and the numeric change
- A **field summary**: how many values changed per field, field types on each side, and fields that exist on one side only
- **Tolerances** for numbers (absolute and relative), and options to ignore case, trim spaces and treat blank text as null, so cosmetic differences do not drown out real ones
- **Duplicate keys** are reported and left out of the comparison rather than matched arbitrarily

Connect the old (before) data to input 1 and the new (after) data to input 2.

## Language
Python

## Inputs
- **Input 1**: the old (before) data.
- **Input 2**: the new (after) data.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Matching | Key fields | `key_fields` | Fields | Identify a record in both inputs. Leave empty to match whole rows. From input 1. |
| Matching | Fields to compare (optional) | `compare_fields` | Fields | Default: all fields in both inputs except keys and ignored fields. From input 1. |
| Matching | Fields to ignore | `ignore_fields` | Fields | For example load timestamps. From input 1. |
| What counts as a change | Numeric tolerance | `tolerance` | Decimal number | Differences up to this amount are not changes. Default: 0.0. |
| What counts as a change | Relative tolerance | `relative_tolerance` | Decimal number | For example 0.001 = 0.1% of the old value. Default: 0.0. |
| What counts as a change | Ignore case | `ignore_case` | Tick box | Text that differs only in upper and lower case is not a change. Default: unticked. |
| What counts as a change | Trim spaces | `trim` | Tick box | Spaces at the start or end of text are ignored. Default: ticked. |
| What counts as a change | Blank text equals null | `blank_is_null` | Tick box | Empty text and a missing value count as the same. Default: ticked. |
| What counts as a change | List unchanged records | `include_unchanged` | Tick box | Default: ticked. |

## Outputs
- **Records** (`records`): One row per record: key, status (Added, Removed, Changed, Unchanged, Duplicate key), number and names of changed fields, row numbers.
- **Differences** (`differences`): One row per changed value: key, field, old value, new value, numeric change.
- **Field summary** (`fields`): Per field: compared, key, only in old, only in new or ignored; types; values changed and share.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the core Compare block

Use the core **Compare** block to check whether two inputs match: fields, record counts and cell values, with allowed differences. Use this block when you need to see *what* changed: it pairs records by key and lists added, removed and changed records with the field-level differences, ready for a report.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
