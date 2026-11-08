# Histogram and Distribution

Histograms with automatic bin widths shared across groups, and distribution statistics (percentiles, skewness, kurtosis) per group.

Bins a numeric field into a **histogram**, overall or **per group**, with the bin width chosen automatically or by you, plus the **summary statistics** analysts look at next.

- Bin width by the **Freedman-Diaconis** rule (twice the interquartile range over the cube root of the count; robust to outliers), **Sturges**, a number of bins, or a fixed width
- The same bins for every group, so histograms line up; optionally clip the range to percentiles so a few extreme values do not squash the chart (values outside are counted as below or above range)
- Statistics per group: count, missing, mean, standard deviation, minimum, P1, P5, quartiles, median, P95, P99, maximum, skewness and excess kurtosis

## Language
Python

## Inputs
- **Input**: data with a numeric field (and an optional group field).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | Value field | `value_field` | Field | The numbers to bin and describe. From input 1. |
|  | Per group (optional) | `group_field` | Field | One histogram per value, all on the same bins so they can be compared. From input 1. |
|  | Bin width rule | `bin_rule` | Choice | How the bin width is chosen when you do not set one. Freedman-Diaconis copes better with outliers. Choices: Freedman-Diaconis; Sturges. Default: Freedman-Diaconis. |
|  | Number of bins (optional) | `bins` | Whole number | 0 = use the rule. Default: 0. |
|  | Bin width (optional) | `bin_width` | Decimal number | 0 = use the rule or the number of bins. Default: 0.0. |
|  | Clip range to percentiles | `clip_percentile` | Decimal number | For example 1 = from P1 to P99; 0 = full range. Default: 0.0. |

## Outputs
- **Histogram** (`histogram`): Per group and bin: from, to, midpoint, count, share, cumulative share.
- **Summary** (`summary`): Per group: count, missing, mean, standard deviation, percentiles, skewness, kurtosis, below / above range.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
