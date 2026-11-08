# ABC Classification

Classifies items into A, B and C by cumulative share of value (Pareto), optionally within groups, plus XYZ demand-variability classes for ABC-XYZ inventory analysis.

The Pareto principle as a block: rank items (products, customers, suppliers) by value and classify them by **cumulative share of the total**:

- **A**: the items that together make the first 80% of value (usually a small share of items)
- **B**: the next 15% (up to 95%)
- **C**: the remaining 5% (usually most items)

Thresholds are options, and classes can be computed **within groups** (per warehouse, category or region). Sales lines are aggregated per item first, so you can feed transactions directly.

Add a **date field** and the block also performs **XYZ analysis**: per item, the coefficient of variation of demand across weeks, months or quarters (periods with no sales count as zero). **X** = steady (CV up to 0.5), **Y** = variable (up to 1.0), **Z** = erratic. Combined classes such as *AX* (high value, steady: automate replenishment) or *CZ* (low value, erratic: consider make-to-order or delisting) are the basis of many inventory policies.

The second output summarises each class: items, value, shares and a suggested policy.

## Language
Python

## Inputs
- **Input 1**: items or sales lines with an item field and a value field (and a date for XYZ).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Data | Item field | `item_field` | Field | Product, SKU, customer or supplier. From input 1. |
| Data | Value field | `value_field` | Field | Value to rank by, such as sales value or margin. Summed per item. From input 1. |
| Data | Classify within (optional) | `group_fields` | Fields | For example Warehouse or Category. From input 1. |
| ABC | A class up to | `a_share` | Decimal number | Cumulative share of value covered by class A. Default: 0.8. |
| ABC | B class up to | `b_share` | Decimal number | Cumulative share covered by classes A and B together. Default: 0.95. |
| XYZ (optional) | Date field (enables XYZ) | `date_field` | Field | Date of each sales line; demand is summed per period. From input 1. |
| XYZ (optional) | Demand field for XYZ | `xyz_field` | Field | Quantity to measure variability on, such as Units. Leave empty to use the value field. From input 1. |
| XYZ (optional) | Period | `period` | Choice | Period that demand is summed over before its variability (CV) is measured. Choices: Month; Week; Quarter. Default: Month. |
| XYZ (optional) | X class up to CV | `x_cv` | Decimal number | Default: 0.5. |
| XYZ (optional) | Y class up to CV | `y_cv` | Decimal number | Default: 1.0. |

## Outputs
- **Classified items** (`items`): Per item: total value, value share, cumulative share, rank, ABC class; with a date field also periods, average per period, coefficient of variation, XYZ class and ABC-XYZ.
- **Class summary** (`classes`): Per (group and) class: items, value, share of items, share of value, suggested policy.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
