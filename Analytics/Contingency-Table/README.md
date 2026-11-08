# Contingency Table and Chi-square

Cross-tabulates two categorical fields with shares, expected counts and residuals, and tests their association with chi-square and Cramer's V.

Cross-tabulates two categorical fields (channel by outcome, region by product, segment by churned) and tests whether they are **associated** or independent.

**Cells output**, one row per combination: count, row share, column share, share of total, expected count under independence, **adjusted standardised residual** (values beyond about +/-2 show the cells that drive the association) and contribution to chi-square.

**Test output**: Pearson **chi-square**, degrees of freedom, **p-value**, **Cramer's V** (strength from 0 = none to 1 = perfect, with a plain-language label), sample size, the smallest expected count (with a caution when cells expect fewer than 5) and a one-sentence **verdict** naming the most over-represented combination.

Optional weight field for pre-aggregated counts, optional segments (one test per segment), Yates continuity correction for 2 x 2 tables. Pure Python.


## Language
Python

## Inputs
- **Input 1**: records with two categorical fields (or an aggregated table with a count field).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Fields | Row field | `row_field` | Field | Category shown down the rows, such as Channel. From input 1. |
| Fields | Column field | `col_field` | Field | Category shown across the columns, such as Outcome. From input 1. |
| Fields | Count / weight field (optional) | `weight_field` | Field | Use when each row is already a count, such as an aggregated table. From input 1. |
| Fields | Test separately for each (optional) | `segment_fields` | Fields | From input 1. |
| Test | Significance level | `alpha` | Decimal number | A p-value below this calls the association significant. Default: 0.05. |
| Test | Yates correction for 2 x 2 tables | `yates` | Tick box | Default: unticked. |
| Test | Include blank values as a category | `include_blank` | Tick box | Default: unticked. |

## Outputs
- **Table cells** (`cells`): One row per row / column combination: count, shares, expected count, adjusted residual, chi-square contribution.
- **Chi-square test** (`test`): Chi-square, degrees of freedom, p-value, Cramer's V, sample size, smallest expected count, verdict.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
