# Period Comparison

Builds the standard month / QTD / YTD / moving annual total comparison versus prior periods per group, with a fiscal year start of your choice, plus a monthly trend table.

The comparison table that finance and trading packs typically start with, per group (region, channel, product), as at a reporting month:

| Column | Meaning |
|---|---|
| Month, Prior Month, Same Month Last Year | the reporting month and its comparators |
| QTD, Prior Year QTD | quarter to date (quarters follow the fiscal year) |
| YTD, Prior YTD | year to date, fiscal year starting in the month you choose (April for many UK organisations) |
| MAT, Prior MAT | moving annual total: the last 12 months, and the 12 before |
| Change and % Change | for month vs prior month, month vs last year, QTD, YTD and MAT |

A *Total* row is added when there are groups. The reporting month is the latest **complete** month in the data unless you set a date. A second output gives the monthly **trend table** per group: value, same month last year, % change, YTD cumulative, MAT and fiscal year label.

Input is transactions or daily / monthly totals with a date and a value; everything is summed by month first.

## Language
Python

## Inputs
- **Input 1**: transactions or daily / monthly totals with a date and a value.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Data | Date field | `date_field` | Field | Date of each value. From input 1. |
| Data | Value field | `value_field` | Field | Sales, revenue, units, cost... From input 1. |
| Data | Group by (optional) | `group_fields` | Fields | One comparison per value, such as Region. From input 1. |
| Periods | Reporting date (optional) | `as_of` | Text | Any date in the reporting month, such as 2025-09-30. Empty = latest complete month in the data. |
| Periods | Fiscal year starts in month | `fiscal_year_start` | Whole number | 1 = January, 4 = April. Default: 1. |
| Periods | Use the latest complete month | `complete_months_only` | Tick box | When no reporting date is set and the last month in the data is partial, report the month before. Default: ticked. |

## Outputs
- **Period comparison** (`comparison`): Per group (and total): month, prior month, same month last year, QTD, YTD, MAT and their comparators, with changes.
- **Monthly trend** (`trend`): Per group and month: value, same month last year, % change, YTD, MAT, fiscal year.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
