# Holt-Winters Forecast

Exponential smoothing forecasts per series with automatic trend and seasonality selection, prediction intervals and a holdout accuracy check.

**Exponential smoothing (Holt-Winters / ETS) forecasts** per series (product, store, region, cost centre) with trend and seasonality.

- Models: level only, **additive or damped trend**, and **no, additive or multiplicative seasonality**; with *Automatic*, the model with the lowest AICc is chosen per series
- Smoothing parameters fitted by least squares
- **Prediction intervals** (80% and 95%) from simulated future paths using the model's own errors, so they widen with the horizon
- Optional **holdout check**: the last N periods are forecast from earlier data and scored (MAE, RMSE, MAPE) against a seasonal naive forecast; **MASE** below 1 means the model beats "same as last season"

Rows are aggregated to day, week, month or quarter (sum); empty periods count as zero. Seasonality needs at least two full seasons of history.

Outputs: actuals with fitted values, holdout forecasts and future forecasts with intervals in one table for charting, and one row per series describing the model and its accuracy. Needs the *scipy* package, which is installed with the block. Fitting takes roughly a second per series.

## Language
Python

## Inputs
- **Input**: history with a date, a value and optional series fields.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| History | Date field | `date_field` | Field | Date of each value; values are summed per period. From input 1. |
| History | Value field | `value_field` | Field | The quantity to forecast, such as sales. From input 1. |
| History | One forecast per (optional) | `series_fields` | Fields | For example Product or Store. From input 1. |
| History | Period | `period` | Choice | Choices: Month; Week; Day; Quarter. Default: Month. |
| Forecast | Horizon (periods) | `horizon` | Whole number | How many periods to forecast past the last one in the data. Default: 12. |
| Forecast | Season length | `season_length` | Whole number | 0 = default for the period (12 months, 52 weeks, 7 days, 4 quarters). Default: 0. |
| Forecast | Trend | `trend` | Choice | Automatic picks the trend with the best fit; a damped trend levels off over the horizon. Choices: Automatic; None; Additive; Damped. Default: Automatic. |
| Forecast | Seasonality | `seasonality` | Choice | Automatic picks the best fit. Multiplicative seasons grow with the level; additive ones stay the same size. Choices: Automatic; None; Additive; Multiplicative. Default: Automatic. |
| Forecast | Holdout check (periods) | `holdout` | Whole number | 0 = no check. Default: 0. |
| Forecast | Simulated paths for intervals | `simulations` | Whole number | Default: 1000. |
| Forecast | Random seed | `seed` | Whole number | Default: 1. |

## Outputs
- **Forecast** (`forecast`): Per series and period: row type (Actual, Holdout forecast, Forecast), actual, fitted, forecast, 80% and 95% intervals, horizon.
- **Models** (`models`): Per series: model chosen, smoothing parameters, AICc, in-sample error, holdout accuracy and MASE.

## Dependencies
scipy

## Source
[script.py](script.py)

## Why this rather than the core Time Series Forecast block

Start with the core **Time Series Forecast** block. Use this block when you need Holt-Winters exponential smoothing fitted separately for many series in one pass, with prediction intervals and a holdout check of accuracy per series.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
