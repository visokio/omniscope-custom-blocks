# Imputation

Fills missing values with the mean, median, mode, a constant, previous / next value or interpolation, optionally within groups, with indicator fields and a summary.

Fills missing values so that totals, averages, charts and models are not thrown off by gaps.

**Number fields**: mean, median, mode, a constant, the previous or next value, or linear interpolation between neighbours.
**Text fields**: the most common value, a constant (such as *Unknown*), or the previous or next value.

- **Within groups**: compute the fill value per group, such as the median floor area *per property type and region*, falling back to the overall value when a group has no data at all
- **Order** for previous / next / interpolation, such as by date within each sensor
- **Sentinel values** such as -999 or 9999 can be treated as missing too
- **Indicator fields** (`<field> Was Imputed`, 1 or 0) so filled values stay visible and can be excluded later
- Integer fields stay whole numbers

The second output summarises each field: method, missing before, imputed, still missing and the value used.

## Language
Python

## Inputs
- **Input 1**: the data with missing values.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Fields | Fields to impute | `fields` | Fields | Leave empty to impute every field (except group and order fields). From input 1. |
| Fields | Within groups (optional) | `group_fields` | Fields | Compute mean / median / mode, and fill previous / next, separately for each combination of these fields. From input 1. |
| Fields | Order by (for previous / next / interpolation) | `order_fields` | Fields | Row order used for previous value, next value and interpolation, usually a date. From input 1. |
| Method | Number fields | `numeric_method` | Choice | Median is robust to outliers and is the usual default. Choices: Median; Mean; Most common value; Constant; Previous value; Next value; Linear interpolation; Leave missing. Default: Median. |
| Method | Text fields | `text_method` | Choice | How missing text is filled. Choices: Most common value; Constant; Previous value; Next value; Leave missing. Default: Most common value. |
| Method | Constant for numbers | `constant_number` | Decimal number | Default: 0.0. |
| Method | Constant for text | `constant_text` | Text | Default: Unknown. |
| Options | Also treat as missing | `extra_missing` | Text | Comma-separated sentinel values, such as -999, 9999, unknown. |
| Options | Fall back to the overall value | `fallback_overall` | Tick box | When a group has no values at all (or interpolation has no neighbour on one side), use the overall statistic or the nearest value. Default: ticked. |
| Options | Add 'Was Imputed' indicator fields | `add_flags` | Tick box | Adds a Yes / No field per imputed field, so filled values stay visible. Default: ticked. |
| Options | Keep whole-number fields whole | `keep_integers` | Tick box | Round imputed values in integer fields. Default: ticked. |

## Outputs
- **Imputed data** (`imputed`): The input with missing values filled, plus '<field> Was Imputed' indicators.
- **Imputation summary** (`summary`): Per field: method, missing before, imputed, still missing, value used.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
