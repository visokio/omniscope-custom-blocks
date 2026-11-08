# Stock Run-Out Projection

Projects stock day by day from on-hand, demand and open purchase orders to give run-out dates, shortfalls and what to expedite.

Projects each item's stock **day by day** from stock on hand, expected **demand** (forecast or orders) and expected **receipts** (open purchase orders, transfers), and reports **when it runs out**.

- **Input 1**: one row per item with stock on hand, and optionally a safety stock and a steady daily demand
- **Input 2** (optional): dated future movements per item with a quantity and a type; types containing *receipt, PO, purchase, transfer in, supply* or *inbound* (your own list) are receipts, anything else is demand
- Per item: **run-out date**, days until run-out, days of cover, first day below **safety stock**, lowest projected stock and **shortfall**, next receipt, and a **status**: *Runs out before next receipt*, *Runs out (receipts too small or late)*, *Below safety stock* or *OK*, sorted with the urgent ones first
- The daily projection (opening, demand, receipts, closing) for charts

Pairs with Safety Stock and Reorder Point (the levels) and Holt-Winters Forecast (the demand).

## Language
Python

## Inputs
- **Input 1**: items with stock on hand (and optional safety stock and daily demand).
- **Input 2 (optional)**: dated movements (demand and receipts).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Items (input 1) | Item field | `item_field` | Field | Identifies the item, such as a SKU. From input 1. |
| Items (input 1) | Stock on hand | `stock_field` | Field | Units on hand at the start date. From input 1. |
| Items (input 1) | Safety stock (optional) | `safety_field` | Field | Level to keep in reserve; days below it are flagged. From input 1. |
| Items (input 1) | Daily demand (optional) | `daily_demand_field` | Field | Steady demand per day, added to any dated demand. From input 1. |
| Movements (input 2, optional) | Item field | `move_item_field` | Field | Item of each movement, matched to input 1. From input 2. |
| Movements (input 2, optional) | Date | `move_date_field` | Field | Date of each demand or receipt. From input 2. |
| Movements (input 2, optional) | Quantity | `move_qty_field` | Field | Units in each movement. From input 2. |
| Movements (input 2, optional) | Type (optional) | `move_type_field` | Field | Receipts vs demand; without it all movements are demand. From input 2. |
| Movements (input 2, optional) | Words that mark a receipt | `receipt_words` | Text | Default: receipt, po, purchase, transfer in, supply, inbound. |
| Projection | Start date (optional) | `start_date` | Text | Default: the first movement date, or today. |
| Projection | Horizon (days) | `horizon_days` | Whole number | Number of days to project. Default: 90. |

## Outputs
- **Items** (`items`): Per item: stock, safety stock, demand and receipts, cover, run-out date, below safety stock, shortfall, next receipt, status.
- **Projection** (`projection`): Per item and day: opening stock, demand, receipts, closing stock.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
