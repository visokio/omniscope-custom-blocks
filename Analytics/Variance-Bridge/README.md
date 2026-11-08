# Variance Bridge

Bridges two totals (budget vs actual, year on year) by category as waterfall steps with favourable / adverse labels, per group.

Explains the difference between **two totals** (budget and actual, last year and this year, forecast and outturn) as a **waterfall of category variances**, ready for a bridge chart.

- Values are summed per category; steps ordered by the **size of the variance** (or by name), with an optional **Other** step for the smaller ones
- Each step has its **bar start and end** for a waterfall chart, and its share of the total variance
- **Favourable / adverse** labels: higher is better for revenue-like measures, lower is better for costs
- Optionally **one bridge per group** (region, business unit)

Price-Volume-Mix Bridge splits a revenue change into price, volume and mix; this block bridges any two totals by category.

## Language
Python

## Inputs
- **Input**: data with a category and two value fields (base and current).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | Category field | `category_field` | Field | Each category becomes a step of the bridge, such as a cost line. From input 1. |
|  | One bridge per (optional) | `group_field` | Field | From input 1. |
|  | Base value (for example Budget) | `base_field` | Field | The value the bridge starts from. From input 1. |
|  | Current value (for example Actual) | `current_field` | Field | The value the bridge ends at. From input 1. |
|  | Base label | `base_label` | Text | Default: Budget. |
|  | Current label | `current_label` | Text | Default: Actual. |
|  | Better when | `better_when` | Choice | Sets which variances are favourable: higher for revenue, lower for costs. Choices: Higher (revenue, profit); Lower (costs). Default: Higher (revenue, profit). |
|  | Order steps by | `order` | Choice | Choices: Size of variance; Category name. Default: Size of variance. |
|  | Steps before Other | `top_n` | Whole number | 0 = all categories. Default: 0. |

## Outputs
- **Bridge** (`bridge`): Steps: base total, category variances, current total, with bar start / end, direction and share of variance.
- **Categories** (`categories`): Per category: base, current, variance, variance %, favourable / adverse.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
