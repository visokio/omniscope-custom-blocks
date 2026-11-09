# Data Cleansing

Removes empty rows and fields, fixes missing values, strips unwanted characters and changes case in one step, with a report of what changed.

The everyday clean-up steps in one block, as a single checklist:

- **Remove empty rows** (every field empty) and **empty fields** (no values at all)
- **Treat placeholders as missing**: list values such as `NULL, N/A, -` and they become real missing values
- **Replace missing values**: blank for text fields, 0 for number fields
- **Remove unwanted characters**: leading and trailing spaces; tabs, line breaks and repeated spaces; all spaces; letters; digits; punctuation; invisible characters such as zero-width and non-breaking spaces
- **Change case**: UPPER, lower or Title Case, optionally only for some fields
- **Convert number text to numbers** once placeholders and symbols are gone (fields with leading zeros, such as phone numbers and codes, stay text)

Choose the fields to cleanse, or leave empty for all fields. The second output reports, per field, how many values changed, so the clean-up is auditable.

## Language
Python

## Inputs
- **Input 1**: the data to cleanse.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Fields | Fields to cleanse | `fields` | Fields | Leave empty to cleanse every field. From input 1. |
| Missing values | Remove empty rows | `remove_null_rows` | Tick box | Drop rows where every field is empty or a placeholder. Default: ticked. |
| Missing values | Remove empty fields | `remove_null_columns` | Tick box | Drop cleansed fields that have no values at all. Default: unticked. |
| Missing values | Placeholders to treat as missing | `null_tokens` | Text | Comma-separated values that mean 'no value', such as NULL, N/A, #N/A, -. Matched ignoring case and surrounding spaces. |
| Missing values | Replace missing text with blank | `replace_null_text` | Tick box | Text fields: missing values become empty text. Inside Omniscope empty text and missing look the same; this matters when exporting to systems that tell them apart. Default: ticked. |
| Missing values | Replace missing numbers with 0 | `replace_null_numbers` | Tick box | Number fields: missing values become 0. Default: ticked. |
| Unwanted characters | Leading and trailing whitespace | `trim` | Tick box | Removes spaces at the start and end of text. Default: ticked. |
| Unwanted characters | Tabs, line breaks and repeated spaces | `collapse_whitespace` | Tick box | Replaced by a single space. Default: unticked. |
| Unwanted characters | All whitespace | `remove_all_whitespace` | Tick box | Default: unticked. |
| Unwanted characters | Letters | `remove_letters` | Tick box | Default: unticked. |
| Unwanted characters | Digits | `remove_numbers` | Tick box | Default: unticked. |
| Unwanted characters | Punctuation | `remove_punctuation` | Tick box | Default: unticked. |
| Unwanted characters | Invisible and non-printable characters | `remove_invisible` | Tick box | Zero-width spaces, control characters and byte-order marks are removed; non-breaking spaces become normal spaces. Default: unticked. |
| Case and types | Change case | `modify_case` | Choice | Changes the case of text, in every cleansed text field or only those chosen below. Choices: Leave as is; UPPER CASE; lower case; Title Case. Default: Leave as is. |
| Case and types | Change case only in | `case_fields` | Fields | Leave empty to change case in every cleansed text field. From input 1. |
| Case and types | Convert number text to numbers | `convert_numbers` | Tick box | After cleansing, a text field whose values are all numbers (currency symbols and thousands separators allowed) becomes a number field. Values with leading zeros keep the field as text. Default: unticked. |

## Outputs
- **Cleansed data** (`cleansed`): The input after cleansing.
- **Cleansing report** (`report`): One row per cleansed field: values changed, placeholders set to missing, missing values filled, and whether the field was removed or converted.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
