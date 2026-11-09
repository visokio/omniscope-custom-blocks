# Date Range Expander

Expands each start / end date range into one row per day, week, month, quarter or year, with days in each period and amounts prorated by days.

Turns each record with a start and an end date into **one row per day, week, month, quarter or year** that the range covers.

Each output row carries the period label, its start and end, the **number of days of the range inside that period** and the share of the whole range. Choose amount fields to **prorate**: a 12-month contract worth 12,000 becomes a value per month weighted by days, ready for revenue recognition, budget phasing or occupancy counts.

- End date inclusive (contracts, leave) or exclusive (hotel check-out, rentals)
- Missing end dates can mean *still active* (today), a single day, or be skipped
- Text dates are parsed, day first by default (31/01/2025)
- Records that cannot be expanded (no start date, end before start) go to the second output with a reason

Weeks run Monday to Sunday; quarters and years are calendar quarters and years.

## Language
Python

## Inputs
- **Input 1**: records with a start date and an end date.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Date range | Start date | `start_field` | Field | Date (or date text) the range starts on. From input 1. |
| Date range | End date | `end_field` | Field | Date (or date text) the range ends on. From input 1. |
| Date range | End date is included | `inclusive_end` | Tick box | Ticked: a range 1 to 3 January covers 3 days (contracts, absences). Unticked: it covers 2 days (hotel nights, rentals). Default: ticked. |
| Date range | When the end date is missing | `missing_end` | Choice | What to do with a range that has no end date. Choices: Use today (still active); Use the start date (one day); Skip the record. Default: Use today (still active). |
| Date range | Text dates are day first | `day_first` | Tick box | Read 03/04/2025 as 3 April (UK style). Untick for 4 March (US style). ISO dates (2025-04-03) are always read correctly. Default: ticked. |
| Periods and amounts | One row per | `frequency` | Choice | Size of the periods each range is split into. Choices: Day; Week (Monday to Sunday); Month; Quarter; Year. Default: Month. |
| Periods and amounts | Amounts to prorate | `prorate_fields` | Fields | Number fields split across periods in proportion to the days in each period. Each gets a new field '<name> (prorated)'. From input 1. |
| Periods and amounts | Maximum periods per record | `max_periods` | Whole number | Safety limit: records spanning more periods than this are skipped. Default: 5000. |

## Outputs
- **Expanded periods** (`expanded`): One row per record and period, with Period, Period Start, Period End, Period Number, Days In Period, Days In Range, Share Of Range and prorated amounts.
- **Skipped records** (`skipped`): Records that could not be expanded, with the reason.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
