# Business Hours and SLA

Elapsed business hours between timestamps within opening hours, excluding weekends and holidays, with SLA due times and met / breached status.

Measures **elapsed working time** between two timestamps (opened and resolved) counting only **opening hours on working days**, skipping weekends and **public holidays**, and checks each item against its **service level**.

- Opening hours such as 09:00 to 17:30; working days Monday to Friday (or Sunday to Thursday, Monday to Saturday, every day)
- Public holidays for England and Wales, Scotland, Northern Ireland or US federal (the rules used by the Working Days block), plus your own closure dates
- SLA targets in **business hours**: from a field, by **priority** (`P1=4, P2=8, P3=24`), or one value for all
- Items still open are measured to the **as-of** time
- Per item: business and calendar hours elapsed, **SLA due** time, status (**Met, Breached, Open, Open and breached**) and business hours to spare or over; per priority: counts, met rate and medians

Overnight shifts (closing after midnight) are not supported.

## Language
Python

## Inputs
- **Input**: items with an opened time and optionally a resolved time, priority or SLA hours.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Items | Opened (start) field | `start_field` | Field | When each item was opened. From input 1. |
| Items | Resolved (end) field | `end_field` | Field | Empty = still open. From input 1. |
| Items | Priority field (optional) | `priority_field` | Field | Priority of each item, for the SLA hours by priority. From input 1. |
| Items | SLA hours field (optional) | `sla_field` | Field | From input 1. |
| Items | SLA hours by priority | `sla_by_priority` | Text | For example: P1=4, P2=8, P3=24, P4=40 |
| Items | SLA hours for everything else | `sla_hours` | Decimal number | 0 = none. Default: 0.0. |
| Items | As of (for open items) | `as_of` | Text | Default: the latest time in the data. |
| Working time | Opening time | `open_time` | Text | Start of the working day, as HH:MM. Default: 09:00. |
| Working time | Closing time | `close_time` | Text | End of the working day, as HH:MM. Default: 17:30. |
| Working time | Weekend | `weekend` | Choice | Choices: Saturday and Sunday; Friday and Saturday; Sunday only; No weekend. Default: Saturday and Sunday. |
| Working time | Public holidays | `region` | Choice | Public holidays that do not count as working time. Choices: England and Wales; Scotland; Northern Ireland; US federal; None. Default: England and Wales. |
| Working time | Extra closure dates | `custom_holidays` | Text | Comma-separated, for example: 2025-12-24, 2025-12-31 |

## Outputs
- **Items** (`items`): The input with business and calendar hours, open flag, SLA hours, SLA due, SLA status and hours to spare.
- **Summary** (`summary`): Per priority and overall: items, closed, open, met, breached, met rate, median hours.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
