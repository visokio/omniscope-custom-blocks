# Price Index

Laspeyres, Paasche and Fisher price indices, value and volume indices from item prices and quantities per period, per group.

Builds **your own price index** from prices and quantities per item and period: a cost index for what you buy, a price index for what you sell, a basket index for a category.

- **Laspeyres** (base-period quantities), **Paasche** (current-period quantities) and **Fisher** (their geometric mean)
- A **value index** and the implied **volume index** (value / Fisher), so spend growth splits into price and volume
- Indices are 100 in the **base period** (default: the first); items need a price in both periods compared, and counts of compared and missing items are shown
- Optionally one index per **group** (category, supplier, region)

Pairs with Inflation Adjustment, which uses an index table to restate values in real terms.

## Language
Python

## Inputs
- **Input**: rows with an item, a period, a unit price and a quantity.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | Item field | `item_field` | Field | Identifies an item whose price is tracked. From input 1. |
|  | Period field | `period_field` | Field | The period of each price and quantity, such as Year. From input 1. |
|  | Unit price field | `price_field` | Field | Price paid per unit. From input 1. |
|  | Quantity field | `quantity_field` | Field | Units bought, used to weight the items. From input 1. |
|  | One index per (optional) | `group_field` | Field | From input 1. |
|  | Base period | `base_period` | Text | Default: the first period. |

## Outputs
- **Index** (`index`): Per group and period: items compared and missing, Laspeyres, Paasche, Fisher, value and volume indices, change.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
