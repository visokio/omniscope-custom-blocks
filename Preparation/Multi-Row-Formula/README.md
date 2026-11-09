# Multi-Row Formula

Window calculations across rows within groups: previous / next value, change, % change, running total, rolling mean / sum / min / max over rows or days, rank and share of group.

Calculations that look at **other rows**: the previous or next value, the change since last time, running totals, rolling averages and ranks, each **within a group** (per store, customer, product) and **in the order you choose** (usually by date).

| Tick | New field (for value field *Sales*) |
|---|---|
| Previous value / Next value | *Sales Previous*, *Sales Next* (any field type) |
| Change / % change | *Sales Change*, *Sales % Change* (vs the previous row) |
| Running total | *Sales Running Total* |
| Rolling mean / sum / min / max | *Sales Rolling Mean (7 days)* and so on |
| Rank in group | *Sales Rank* (1 = highest) |
| Share of group total | *Sales Share Of Group* |
| Row number in group | *Row Number* |

Rolling windows count either **rows** (the last 7 records) or **days** (the last 7 calendar days, so gaps in the data are handled properly). The output keeps the input order unless you untick that option.

## Language
Python

## Inputs
- **Input 1**: the data, one row per record (for example one row per store per day).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Fields | Value fields | `value_fields` | Fields | Fields to calculate on. Previous / next work for any field; the other calculations need numbers. From input 1. |
| Fields | Group by (optional) | `group_fields` | Fields | Calculations restart for each combination of these fields, for example Store or Customer. From input 1. |
| Fields | Order by | `sort_fields` | Fields | Order of rows within each group, usually a date. For rolling windows in days choose exactly one date field. From input 1. |
| Calculations | Previous value | `calc_previous` | Tick box | Default: ticked. |
| Calculations | Next value | `calc_next` | Tick box | Default: unticked. |
| Calculations | Change vs previous | `calc_change` | Tick box | Default: ticked. |
| Calculations | % change vs previous | `calc_pct_change` | Tick box | As a fraction: 0.05 means up 5%. Default: unticked. |
| Calculations | Running total | `calc_running_total` | Tick box | Cumulative sum within each group. Default: unticked. |
| Calculations | Rolling mean | `calc_rolling_mean` | Tick box | Average over the rolling window. Default: unticked. |
| Calculations | Rolling sum | `calc_rolling_sum` | Tick box | Default: unticked. |
| Calculations | Rolling minimum | `calc_rolling_min` | Tick box | Default: unticked. |
| Calculations | Rolling maximum | `calc_rolling_max` | Tick box | Default: unticked. |
| Calculations | Rank in group | `calc_rank` | Tick box | 1 = highest value in the group; ties share the lower rank. Default: unticked. |
| Calculations | Share of group total | `calc_share` | Tick box | Default: unticked. |
| Calculations | Row number in group | `calc_row_number` | Tick box | Default: unticked. |
| Offsets and windows | Rows back / forward | `offset` | Whole number | For previous, next and change: 1 compares with the row just before; 7 with daily data compares with the same weekday last week. Default: 1. |
| Offsets and windows | Rolling window size | `window` | Whole number | Rows or days in each rolling window. Default: 7. |
| Offsets and windows | Rolling window counts | `window_unit` | Choice | Whether the window counts rows or days of the date in Order by. Choices: Rows; Days (uses the date in Order by). Default: Rows. |
| Offsets and windows | Only when the window is full | `full_window` | Tick box | Leave rolling values empty until a full window of rows (or days) is available. Default: unticked. |
| Order | Order descending | `descending` | Tick box | Tick to process newest first. Default: unticked. |
| Order | Keep input row order | `keep_order` | Tick box | Untick to output rows sorted by group and order fields. Default: ticked. |

## Outputs
- **Output 1** (`Output Data`): The input with the new calculated fields.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
