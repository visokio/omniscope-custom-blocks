# Price-Volume-Mix Bridge

Decomposes revenue change between two periods into volume, mix, price, new and lost product effects that add up exactly, per item and optional group.

Explains *why* revenue changed between a base period and a current period, the bridge finance and commercial teams present every month or year:

- **Volume**: more or fewer units overall, valued at base prices and base mix
- **Mix**: customers buying more of the higher- or lower-priced items
- **Price**: price changes on the units sold in the current period
- **New products** and **Lost products**: revenue from items sold in only one of the two periods

The effects are computed per item (product, SKU, service) and **add up exactly** to the revenue change. Optionally per group (region, channel). The bridge output has one row per step with start and end values for a waterfall chart; the item output shows every item's volumes, prices and effects.

Choose the period field and the two values to compare (by default the first and last values in sort order).

## Language
Python

## Inputs
- **Input 1**: sales with a period field, an item field, volume and revenue.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Data | Period field | `period_field` | Field | For example Year, or a field with values such as FY24 / FY25. From input 1. |
| Data | Item field | `item_field` | Field | The level at which price and mix are measured, such as Product or SKU. From input 1. |
| Data | Volume field | `volume_field` | Field | Units, kilograms, contracts... From input 1. |
| Data | Revenue field | `revenue_field` | Field | Revenue for the item in the period; price is revenue divided by volume. From input 1. |
| Data | Bridge separately for each (optional) | `group_fields` | Fields | For example Region. From input 1. |
| Periods | Base period value | `base_period` | Text | Empty = the first value of the period field. |
| Periods | Current period value | `current_period` | Text | Empty = the last value of the period field. |

## Outputs
- **Bridge** (`bridge`): Per (group and) step: base revenue, volume, mix, price, new, lost, current revenue, with bar start / end for waterfall charts.
- **Item effects** (`items`): Per (group and) item: status, volumes, revenues, prices, volume / mix / price / new-lost effects.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
