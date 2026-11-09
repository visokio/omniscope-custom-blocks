# Seasonal Decomposition

Splits time series into trend, seasonal and residual components (additive or multiplicative) with seasonally adjusted values, seasonal indices and strength measures.

Explains a time series rather than forecasting it: how much is **trend**, how much is the **seasonal** pattern that repeats every year (or week), and what is left over (**residual**: promotions, one-offs, noise).

- Classical decomposition with a centred moving average, **additive** (seasonal effect in units) or **multiplicative** (seasonal effect in %)
- **Seasonally adjusted** values: the series with the seasonal pattern removed, so month-on-month changes mean something
- **Seasonal indices** per season (January to December, Q1 to Q4, Monday to Sunday) with the effect versus trend
- Per series: **seasonality strength** and **trend strength** (0 to 1), peak and trough season, trend change over the period, residual spread
- Several series at once (per category, store, region); duplicate dates are summed and missing periods interpolated (and flagged); the trend can be extended to the ends of the series

Needs at least two full seasons per series. Complements Omniscope's Time Series Forecast block: decompose to understand, forecast to plan.

## Language
Python

## Inputs
- **Input 1**: one or more regular time series (date, value, optional series fields).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Series | Date field | `date_field` | Field | Date of each value. From input 1. |
| Series | Value field | `value_field` | Field | The series to decompose, such as monthly sales. From input 1. |
| Series | Series (optional) | `group_fields` | Fields | One decomposition per combination of these fields, such as Category. From input 1. |
| Series | Data frequency | `frequency` | Choice | Spacing of the data, which sets the default season length. Choices: Monthly; Quarterly; Weekly; Daily. Default: Monthly. |
| Decomposition | Model | `model` | Choice | Multiplicative when the seasonal swing grows with the level; additive when it stays the same size. Choices: Additive (seasonal effect in units); Multiplicative (seasonal effect in %). Default: Additive (seasonal effect in units). |
| Decomposition | Season length (optional) | `season_length` | Whole number | Periods per cycle. 0 = automatic: 12 for monthly, 4 quarterly, 52 weekly, 7 daily. Default: 0. |
| Decomposition | Extend the trend to the ends | `extend_trend` | Tick box | Fill the first and last half-season of the trend with a straight-line continuation. Default: ticked. |

## Outputs
- **Components** (`components`): One row per series and period: value, trend, seasonal, residual, seasonally adjusted, interpolated flag.
- **Seasonal indices** (`indices`): One row per series and season: seasonal index and effect versus trend.
- **Summary** (`summary`): Per series: seasonality and trend strength, peak and trough season, trend change, residual spread.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
