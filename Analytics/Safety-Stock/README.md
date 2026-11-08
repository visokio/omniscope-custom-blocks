# Safety Stock and Reorder Point

Calculates safety stock, reorder points, order-up-to levels and EOQ per item from demand history and lead times for a target service level, with a reorder list.

Sets stock levels from demand history for a target **service level** (the chance of not running out during a replenishment lead time):

| Output | Formula |
|---|---|
| Average demand, standard deviation | per period (day, week, month); periods with **no demand count as zero** |
| **Safety stock** | z x sqrt(L x sd_d² + d² x sd_L²), with z from the service level, L the lead time and sd_L its variability |
| **Reorder point** | d x L + safety stock |
| **Order-up-to level** | for periodic review: d x (L + R) + z x sqrt((L + R) x sd_d² + d² x sd_L²) |
| **EOQ** | sqrt(2 x annual demand x ordering cost / (holding rate x unit cost)), when costs are given |
| Cover, status, suggested order | from stock on hand: items at or below the reorder point and the quantity to bring them to the order-up-to level |

Input 1 is demand history (item, date, quantity: orders or daily sales lines). Optional input 2 has one row per item with its lead time (in periods), lead-time standard deviation, unit cost, stock on hand and an item-specific service level. Without input 2, one lead time applies to all items.

## Language
Python

## Inputs
- **Input 1**: demand history (item, date, quantity).
- **Input 2 (optional)**: item parameters (lead time, its std dev, unit cost, stock on hand, service level).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Demand (input 1) | Item field | `item_field` | Field | Identifies the item, such as a part number. From input 1. |
| Demand (input 1) | Date field | `date_field` | Field | Date of each demand record; demand is summed per period. From input 1. |
| Demand (input 1) | Quantity field | `quantity_field` | Field | Quantity demanded or shipped. From input 1. |
| Policy | Demand period | `period` | Choice | Lead times and review periods are in this unit. Choices: Week; Day; Month. Default: Week. |
| Policy | Target service level | `service_level` | Decimal number | 0.95 = 95% chance of no stock-out per replenishment cycle. Default: 0.95. |
| Policy | Lead time (periods) | `lead_time` | Decimal number | Used when input 2 gives none. Default: 2.0. |
| Policy | Review period (periods) | `review_period` | Decimal number | Time between stock reviews, for the order-up-to level. Default: 1.0. |
| Policy | Cost per order | `ordering_cost` | Decimal number | For EOQ. 0 = no EOQ. Default: 0.0. |
| Policy | Annual holding cost rate | `holding_rate` | Decimal number | Share of unit cost per year, such as 0.25. Default: 0.25. |
| Item parameters (input 2, optional) | Item field | `param_item_field` | Field | From input 2. |
| Item parameters (input 2, optional) | Lead time | `param_lead_field` | Field | From input 2. |
| Item parameters (input 2, optional) | Lead time std dev | `param_lead_sd_field` | Field | From input 2. |
| Item parameters (input 2, optional) | Unit cost | `param_cost_field` | Field | From input 2. |
| Item parameters (input 2, optional) | Stock on hand | `param_stock_field` | Field | From input 2. |
| Item parameters (input 2, optional) | Service level override | `param_service_field` | Field | From input 2. |

## Outputs
- **Stock levels** (`levels`): Per item: demand statistics, lead time, service level, z, safety stock, reorder point, order-up-to level, EOQ, cover, status, suggested order.
- **Reorder list** (`reorder`): Items at or below their reorder point, least cover first, with the suggested order quantity.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
