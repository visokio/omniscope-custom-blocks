# Age and Tenure

Exact age or service in years, months and days, decimal years, bands, next anniversary and upcoming milestones, with 29 February handled.

Exact **age or length of service** between a start date (date of birth, joining date, contract start) and an as-of date.

- **Completed years, months and days**, and **decimal years**
- A **band** from your boundaries (default 18, 25, 35, 45, 55, 65 gives *Under 18, 18-24, 25-34...65+*; a band one year wide is labelled with that year alone, such as *1*), with a count per band
- The **next anniversary** and the days until it, and an **upcoming milestone** flag (for example 10 years' service within 90 days)
- Someone born on 29 February has their anniversary on 28 February in non-leap years
- An optional **end date** (for example a leaving date) is used instead of the as-of date where it is filled; leavers (an end date before the as-of date) get no upcoming milestone

## Language
Python

## Inputs
- **Input**: data with a start date (and optional end date).

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Start date (birth, joining) | `start_field` | Field | From input 1. |
| End date (optional) | `end_field` | Field | For example a leaving date. From input 1. |
| As of date | `as_of` | Text | Default: today. |
| Band boundaries (years) | `bands` | Text | Default: 18, 25, 35, 45, 55, 65. |
| Milestones (years) | `milestones` | Text | Default: 5, 10, 15, 20, 25, 30, 40. |
| Milestone window (days) | `milestone_window_days` | Whole number | Default: 90. |
| Prefix for new fields (optional) | `prefix` | Text | For example 'Age ' or 'Service '. |

## Outputs
- **Rows** (`rows`): The input with years, months, days, decimal years, band, next anniversary, days to it and upcoming milestone.
- **Bands** (`bands`): Rows and share per band.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
