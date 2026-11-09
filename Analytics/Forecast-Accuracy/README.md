# Forecast Accuracy

Compares forecasts with actuals per item and model: MAE, RMSE, MAPE, sMAPE, WAPE, bias and tracking signal, with flags, best model per item and a model ranking.

Measures how good forecasts are, for one model or several side by side (statistical forecast, sales team, naive), per item and overall:

| Measure | Meaning |
|---|---|
| MAE, RMSE | average absolute error, and root mean squared error (punishes big misses) |
| MAPE, sMAPE | average percentage error (rows with actual 0 excluded), and its symmetric version |
| **WAPE**, Accuracy | total absolute error / total actual (the measure most supply chains report), and 1 - WAPE |
| **Bias** | total (forecast - actual) / total actual: positive = over-forecasting |
| **Tracking signal** | cumulative error / MAE in period order; beyond about +/-4 the forecast is consistently off |

Items with bias beyond a limit or an out-of-control tracking signal are **flagged**, each item's **best model** is marked, and the models are ranked overall. A row-level output gives every error for charts and drill-down.

Input: one row per item and period with the actual and one or more forecast fields.

## Language
Python

## Inputs
- **Input 1**: one row per item and period with the actual and one or more forecast fields.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Data | Actual field | `actual_field` | Field | The value that actually happened, such as units sold. From input 1. |
| Data | Forecast fields | `forecast_fields` | Fields | One or more forecasts (models) to evaluate. From input 1. |
| Data | Item fields (optional) | `item_fields` | Fields | For example SKU, or SKU and Location. From input 1. |
| Data | Period field (optional) | `period_field` | Field | Orders rows for the tracking signal. From input 1. |
| Rules | Pick the best model by | `best_by` | Choice | The measure used to pick each item's best model and to rank the models. Choices: WAPE; MAE; RMSE; MAPE; Accuracy. Default: WAPE. |
| Rules | Bias limit | `bias_limit` | Decimal number | Flag items whose bias exceeds this (0.1 = 10%). Default: 0.1. |
| Rules | Tracking signal limit | `tracking_limit` | Decimal number | Default: 4.0. |

## Outputs
- **Accuracy by item** (`items`): Per item and model: periods, totals, MAE, RMSE, MAPE, sMAPE, WAPE, accuracy, bias, tracking signal, flags, rank, best model.
- **Accuracy by model** (`models`): Per model: the same measures over all items, items where best, rank.
- **Errors by row** (`errors`): Per item, period and model: actual, forecast, error, absolute and percentage error.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
