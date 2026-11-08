# Date Dimension

Generates a calendar table: calendar and ISO weeks, fiscal periods for any year start, UK or US public holidays, working-day counts and flags.

Generates a **calendar table** (date dimension) with one row per day, to join to any fact table and to drive report filters.

- Calendar year, quarter, month (number, name, short name), day of month, day of year, day of week, **ISO week** and ISO year, week start
- **Fiscal year, quarter and period** for a fiscal year starting in any month, named *FY2026*, *FY2025* or *FY 2025/26*
- **Public holidays** for England and Wales, Scotland, Northern Ireland or US federal (with substitute days and announced one-off changes), plus your own dates
- **Working days**: flag, n-th working day of the month, working days in the month and left in the month, last working day, next and previous working day
- Month, quarter and year start / end flags, leap years
- Optional days, months and years relative to a reference date (or *TODAY*) for rolling filters

The range comes from the start and end dates, or from the dates in a field of the optional input (rounded out to whole years by default). A second output lists the holidays in the range.

## Language
Python

## Inputs
- **Input (optional)**: any data with a date field, to set the range.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Range | Start date | `start_date` | Text | For example 2024-01-01. Optional when a date field is chosen. |
| Range | End date | `end_date` | Text | For example 2026-12-31. |
| Range | Or take the range from this field (optional) | `date_field` | Field | With data connected, the calendar covers this field's earliest to latest date. From input 1. |
| Range | Round the range out to whole years | `whole_years` | Tick box | Extends a range taken from a field to 1 January and 31 December. Default: ticked. |
| Calendar rules | Fiscal year starts in month | `fiscal_year_start` | Whole number | 1 = January, 4 = April. Default: 1. |
| Calendar rules | Fiscal year named by | `fiscal_label` | Choice | How the fiscal year is named in the output. Choices: Year it ends (FY2026); Year it starts (FY2025); Both years (FY 2025/26). Default: Year it ends (FY2026). |
| Calendar rules | Public holidays | `region` | Choice | Which public holidays are marked and left out of working days. Choices: England and Wales; Scotland; Northern Ireland; US federal; None. Default: England and Wales. |
| Calendar rules | Weekend | `weekend` | Choice | Days that are not working days. Choices: Saturday and Sunday; Friday and Saturday; Sunday only; No weekend. Default: Saturday and Sunday. |
| Calendar rules | Extra holidays | `custom_holidays` | Text | Comma-separated, for example: 2025-12-24=Christmas Eve, 2025-12-31=Office closed |
| Calendar rules | Reference date (optional) | `reference_date` | Text | A date or TODAY, for the relative fields. |

## Outputs
- **Calendar** (`calendar`): One row per day with calendar, ISO week, fiscal, holiday and working-day fields.
- **Holidays** (`holidays`): The holidays in the range: date, name, day name, year.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
