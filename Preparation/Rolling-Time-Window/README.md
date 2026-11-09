# Rolling Time Window

Trailing time-window aggregates per key (count, sum, mean, min, max, distinct) for several windows, such as transactions per card in the last 24 hours.

For every row, aggregates the rows of the **same key** within a **trailing time window** ending at its timestamp: transactions in the last 24 hours per card, orders in the last 30 days per customer, alarms in the last hour per machine.

- Windows are measured in **time**, not rows, so irregular data is handled correctly; several windows at once (`1h, 24h, 7d, 30d`)
- Per window: **count**, **sum**, **mean**, **minimum** and **maximum** of a value, and **distinct** values of another field (for example distinct merchants)
- Include or exclude the current row (excluded is typical for fraud and velocity features)

Multi-Row Formula covers windows of a fixed number of rows; this block covers windows of a fixed length of time. Minimum, maximum and distinct counts are computed for keys with up to 50,000 rows.

## Language
Python

## Inputs
- **Input**: events with a key and a timestamp (and optional value and distinct fields).

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Key field | `key_field` | Field | For example Card or Customer. From input 1. |
| Timestamp field | `time_field` | Field | Date and time of each event. From input 1. |
| Value field (optional) | `value_field` | Field | The amount to sum, average and take the minimum and maximum of. From input 1. |
| Count distinct (optional) | `distinct_field` | Field | For example Merchant. From input 1. |
| Windows | `windows` | Text | For example: 30min, 1h, 24h, 7d, 4w Default: 1h, 24h, 7d, 30d. |
| Include the current row | `include_current` | Tick box | Unticked, each window covers only earlier rows: useful for scoring a new transaction against its history. Default: ticked. |

## Outputs
- **Rows** (`rows`): The input with count, sum, mean, min, max and distinct per window.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
