# Subtotals and Rollup

Aggregates by a hierarchy of fields with subtotal rows at every level and a grand total, shares of parent and total, in report order.

Aggregates by a **hierarchy of fields** (for example *Division > Region > Site*) and adds a **subtotal row for every level** and a **grand total**, in report order, as in a finance or management table.

- Each row has its **level**, a **row type** (Detail, Subtotal, Grand total) and an **indented label** (one dot per level, for example *· · Leeds*) ready for a table view
- Sum, mean, median, minimum, maximum or count of one or more value fields, plus the number of rows
- For the first value field: **share of parent** and **share of grand total**
- Children sorted by value (largest first) or by name; subtotals before or after their children

An *Order* field keeps the report order whatever the downstream sorting.

## Language
Python

## Inputs
- **Input**: data with the group fields and value fields.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Group fields, outermost first | `group_fields` | Fields | For example Division, Region, Site. From input 1. |
| Value fields | `value_fields` | Fields | The numbers to aggregate at every level. From input 1. |
| Aggregate | `aggregation` | Choice | How values are combined into subtotals. Choices: Sum; Mean; Median; Minimum; Maximum; Count of values. Default: Sum. |
| Order children by | `sort` | Choice | Order of rows under each subtotal. Choices: First value, largest first; Name. Default: First value, largest first. |
| Subtotals | `subtotal_position` | Choice | Choices: Before their children; After their children. Default: Before their children. |
| Grand total row | `grand_total` | Tick box | Default: ticked. |
| Total label | `total_label` | Text | Default: Total. |

## Outputs
- **Rollup** (`rollup`): Order, group fields, level, row type, indented label, rows, values, share of parent, share of total.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
