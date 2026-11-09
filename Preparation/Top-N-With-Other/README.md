# Top N With Other

Keeps the top N items per group by value and rolls the rest into an Other row, with ranks, shares and cumulative shares.

Keeps the **N largest items per group** and rolls everything else into one **Other** row, so charts and tables stay readable: top 10 products per region, top 5 suppliers per category plus Other.

- Values are summed per group and item first; ties are broken by name so results are repeatable
- Optionally also require a **minimum share** of the group (or use only the share, with N = 0)
- Extra value fields (units, margin) are carried along and summed into Other too
- Each row has its **rank**, **share of group**, **cumulative share** and, for Other, how many items it holds

## Language
Python

## Inputs
- **Input**: data with an item field and a value field.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Item field | `item_field` | Field | For example Product or Supplier. From input 1. |
| Rank by value | `value_field` | Field | The number items are ranked on, such as revenue. From input 1. |
| Per group (optional) | `group_fields` | Fields | For example Region. From input 1. |
| Other values to carry (optional) | `extra_value_fields` | Fields | Other numbers to total into the Other row alongside the ranking value. From input 1. |
| Top N | `top_n` | Whole number | 0 = no limit (use the minimum share). Default: 10. |
| Minimum share of group | `min_share` | Decimal number | For example 0.02; 0 = none. Default: 0.0. |
| Add an Other row | `include_other` | Tick box | Adds a row totalling the items outside the top N. Default: ticked. |
| Label for Other | `other_label` | Text | Default: Other. |

## Outputs
- **Top N with Other** (`top`): Per group: kept items and an Other row, with rank, values, share of group, cumulative share, items included.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
