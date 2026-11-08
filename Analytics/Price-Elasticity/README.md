# Price Elasticity

Estimates price elasticity of demand per product with a log-log regression (optional control drivers), with confidence intervals, revenue impact and demand curves.

Estimates how sensitive demand is to price, per product or segment, from historical price and volume observations (for example weekly sales).

The model is the standard **log-log regression**: log(volume) = a + b x log(price) (+ optional control drivers such as a promotion flag, distribution or seasonal dummies). The **elasticity** b means a 1% price rise changes volume by about b%:

- |b| > 1, **elastic**: a price rise loses more volume than it gains in price, so revenue falls
- |b| < 1, **inelastic**: a price rise raises revenue

Per product you get the elasticity, its **confidence interval** and **p-value**, R squared, the observed price range, the estimated **volume and revenue effect** of a chosen price change and a one-line interpretation (including a warning when volume appears to rise with price, a sign of confounding). A **demand curve** output gives predicted volume and revenue across the observed price range, and an observations output adds fitted volumes.

Estimates are only as good as the price variation in the data: prices that never change give no estimate, and effects outside the observed price range are extrapolation.

## Language
Python

## Inputs
- **Input 1**: price and volume observations (for example weekly), per product or segment.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Data | Price field | `price_field` | Field | Price for each observation, such as the average price in a week. From input 1. |
| Data | Volume field | `volume_field` | Field | Units sold (or another quantity). From input 1. |
| Data | Estimate separately for each | `group_fields` | Fields | For example Product, or Product and Region. From input 1. |
| Model | Control drivers (optional) | `control_fields` | Fields | Numeric drivers to hold constant, such as a 0 / 1 promotion flag. From input 1. |
| Model | Confidence level | `confidence` | Decimal number | For the confidence interval on each elasticity. Default: 0.95. |
| Model | Price change to evaluate (%) | `price_change_pct` | Decimal number | Used for the volume and revenue effect columns. Default: 5.0. |
| Model | Minimum observations | `min_observations` | Whole number | Default: 12. |

## Outputs
- **Elasticities** (`elasticities`): Per product: elasticity, confidence interval, p-value, R squared, price range, volume and revenue effect, interpretation.
- **Demand curves** (`curves`): Per product: predicted volume and revenue at 25 prices across the observed range.
- **Observations** (`observations`): The input with Fitted Volume and Used In Model.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
