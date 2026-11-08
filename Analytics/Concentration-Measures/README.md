# Concentration Measures

HHI, Gini, top-N and top-20% shares and Lorenz curves for customer, supplier or market concentration, per group.

Measures **how concentrated a total is** among the entities that make it up: customers in revenue, suppliers in spend, firms in a market, products in sales, overall and per group (market, region, year).

- **HHI** (Herfindahl-Hirschman index: sum of squared percentage shares, 0 to 10,000), normalised HHI and the **equivalent number of equal-sized entities**
- **Gini coefficient** and the **Lorenz curve** (101 points per group, ready to chart against the equality line)
- **Top-1, top-4 (CR4) and top-10 shares**, the share held by the **top 20%** of entities, and how many entities make up **50% and 80%** of the total
- An **HHI band** with thresholds you can set (defaults 1,500 and 2,500, the bands used in the 2010 US Horizontal Merger Guidelines)

Values are summed per entity first; entities with zero or negative totals are left out. Outputs: the measures per group, the Lorenz curve, and each entity with share, rank and cumulative share.

## Language
Python

## Inputs
- **Input**: data with an entity field and a value field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | Entity field | `entity_field` | Field | For example Customer, Supplier or Company. From input 1. |
|  | Value field | `value_field` | Field | For example Revenue or Spend. From input 1. |
|  | Per group (optional) | `group_fields` | Fields | For example Year or Market. From input 1. |
|  | HHI: moderately concentrated from | `hhi_moderate` | Decimal number | HHI at or above this is labelled moderately concentrated. Default: 1500.0. |
|  | HHI: highly concentrated above | `hhi_high` | Decimal number | HHI above this is labelled highly concentrated. Default: 2500.0. |

## Outputs
- **Summary** (`summary`): Per group: entities, total, HHI, normalised HHI, equivalent entities, Gini, top shares, entities for 50% / 80%, band.
- **Lorenz curve** (`lorenz`): Per group: 101 points of cumulative share of entities vs cumulative share of total.
- **Entities** (`entities`): Per group and entity: value, share, rank, cumulative share, in top 20%.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
