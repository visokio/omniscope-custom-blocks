# Time Series Anomaly Detection

Flags spikes and dips per series against a robust rolling median and MAD baseline with weekday effects, centred or trailing.

Flags **unusual days, weeks or months** in one or many time series (per store, product, region, sensor, account) against a robust baseline.

- Optionally **aggregates** rows to day, week or month (sum, mean or count of rows); empty periods count as zero for sums and counts, so a missing day of data shows up
- For daily data, a **weekday effect** is allowed for, so a quiet Sunday or a busy Saturday is not an anomaly (automatic, always, or off)
- **Baseline**: rolling median of the series, **centred** for reviewing history or **trailing** (past only) to mimic live monitoring
- **Robust z-score**: (value - expected) / (1.4826 x rolling MAD). The median and MAD are not pulled about by the anomalies themselves
- |z| above the threshold (3.5 by default) is a **spike** or a **dip**; lower and upper bounds are included for charting a band

Outputs: every period with expected value, bounds, z and flag; the anomalies ranked by severity; and a summary per series with the latest status.

## Language
Python

## Inputs
- **Input**: data with a date, a value (or rows to count) and optional series fields.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Series | Date field | `date_field` | Field | Date of each value. From input 1. |
| Series | Value field | `value_field` | Field | Not needed when counting rows. From input 1. |
| Series | One series per (optional) | `series_fields` | Fields | For example Region or Store. From input 1. |
| Series | Period | `period` | Choice | Choices: Day; Week; Month; As in the data. Default: Day. |
| Series | Aggregate by | `aggregation` | Choice | Choices: Sum; Mean; Count rows; None (one row per period). Default: Sum. |
| Detection | Weekday effect (daily data) | `seasonality` | Choice | Allows for regular weekday patterns, so a busy Saturday is not flagged. Automatic tests whether the pattern is there. Choices: Automatic; Always; None. Default: Automatic. |
| Detection | Baseline | `mode` | Choice | Centred uses periods on both sides, for reviewing history. Trailing uses only earlier ones, as a live check would. Choices: Centred (review history); Trailing (as if live). Default: Centred (review history). |
| Detection | Window (periods) | `window` | Whole number | For example 28 days. Default: 28. |
| Detection | Minimum periods to score | `min_history` | Whole number | Default: 14. |
| Detection | Threshold (robust z) | `threshold` | Decimal number | 3.5 is a common choice; lower flags more. Default: 3.5. |
| Detection | Flag | `direction` | Choice | Choices: Spikes and dips; Spikes only; Dips only. Default: Spikes and dips. |

## Outputs
- **Series** (`series`): Every period: value, expected, bounds, weekday effect, robust z, anomaly flag, deviation.
- **Anomalies** (`anomalies`): Spikes and dips ranked by severity.
- **Summary** (`summary`): Per series: periods, spikes, dips, latest value and status, largest z.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
