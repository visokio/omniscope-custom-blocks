# Time Series Filler

Inserts missing days, weeks, months or other periods in each time series and fills values with zero, the previous value or interpolation, with a gap report.

Transaction extracts only contain the days something happened: a product with no sales on Tuesday simply has no Tuesday row. Averages, charts and forecasts then silently skip the zero days.

Time Series Filler inserts the **missing periods** in each series (per product, store, sensor...) so every series has one row per hour, day, week, month, quarter or year, then fills the value fields:

- **Zero**: no row means nothing happened (sales, transactions, incidents)
- **Previous value**: the last known value carries forward (prices, balances, stock levels)
- **Linear interpolation**: straight line between known values (readings, temperatures)
- **Leave empty**: insert the rows, keep the values missing

Each series runs from its own first to last period, from the overall first to last period (so all series line up), or over a custom range. Inserted rows are flagged (*Is Inserted* = 1) and other fields can be carried forward. The second output reports, per series, expected and present periods, how many were inserted and the longest gap.

Weeks run Monday to Sunday.

## Language
Python

## Inputs
- **Input 1**: time series data with a date field (one or many series).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Series | Date field | `date_field` | Field | Date or date-time of each record. From input 1. |
| Series | Series (optional) | `group_fields` | Fields | One series per combination of these fields, such as Product or Store and Product. From input 1. |
| Series | One row per | `frequency` | Choice | The period to insert missing rows at. Choices: Hour; Day; Week (Monday to Sunday); Month; Quarter; Year. Default: Day. |
| Filling | Value fields to fill | `value_fields` | Fields | Fields to fill in inserted rows. From input 1. |
| Filling | Fill with | `fill_method` | Choice | What the value fields get in inserted rows. Choices: Zero; Previous value; Linear interpolation; Leave empty. Default: Zero. |
| Filling | Carry other fields forward | `carry_other` | Tick box | Copy the remaining fields (such as Category) from the previous row into inserted rows. Default: ticked. |
| Range | Each series runs | `span` | Choice | Where each series starts and ends: its own data, the whole dataset or a custom range. Choices: From its own first to last period; From the overall first to last period; Over a custom range. Default: From its own first to last period. |
| Range | Custom range start | `range_start` | Text | For example 2025-01-01. |
| Range | Custom range end | `range_end` | Text | For example 2025-12-31. |
| Range | Text dates are day first | `day_first` | Tick box | Read 03/04/2025 as 3 April. Default: ticked. |

## Outputs
- **Filled series** (`filled`): Every series with one row per period; Period label and Is Inserted flag added.
- **Gap report** (`gaps`): Per series: first and last period, expected and present periods, inserted periods, longest gap, completeness.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
