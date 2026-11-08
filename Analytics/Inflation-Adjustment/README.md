# Inflation Adjustment

Restates money values in real terms of a base period using a price index table, per series, with the index used and cumulative inflation.

Restates money values in **real terms** (the prices of a base period) using a **price index table** you provide, such as a consumer or producer price index, optionally per country or index series.

- Each row takes the index **in force at its date** (the latest index period on or before it, up to a maximum age)
- Real value = nominal value x index at base / index at the row's date, for one or more money fields
- **Base period** of your choice (default: the latest index period); months can be written as *2025-06*
- The index table comes back with **cumulative inflation to the base**, month-on-month and year-on-year change

Rows that cannot be adjusted (no date, no index early enough, index too old) say why. No index data is included: connect the published series you use.

## Language
Python

## Inputs
- **Input 1**: values with a date and money fields.
- **Input 2**: a price index table (period, value, optional key).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Values (input 1) | Date field | `date_field` | Field | Date of each value, matched to the index period it falls in. From input 1. |
| Values (input 1) | Money fields to adjust | `value_fields` | Fields | Money amounts to restate in base-period prices; each gets a new real-terms field. From input 1. |
| Values (input 1) | Key (optional) | `key_field` | Field | For example Country, matched to the index key. From input 1. |
| Price index (input 2) | Index period | `index_date_field` | Field | The month or date each index value applies to. From input 2. |
| Price index (input 2) | Index value | `index_value_field` | Field | The price index, such as CPI. From input 2. |
| Price index (input 2) | Index key (optional) | `index_key_field` | Field | From input 2. |
| Price index (input 2) | Base period | `base_period` | Text | A date or month, for example 2025-06. Default: latest index period. |
| Price index (input 2) | Maximum index age (days) | `max_age_days` | Whole number | Default: 400. |
| Price index (input 2) | Suffix for real-terms fields | `suffix` | Text | Default:  (real). |

## Outputs
- **Rows** (`rows`): The input with index period used, index at date and at base, inflation factor, real values and status.
- **Index** (`index`): The index table with inflation to base, month-on-month and year-on-year change.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
