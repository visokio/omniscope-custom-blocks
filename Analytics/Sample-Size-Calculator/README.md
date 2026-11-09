# Sample Size Calculator

Sample size and power for A/B tests on proportions or means and for survey margins of error, per scenario, with days needed and power curves.

Works out **how many observations an A/B test or survey needs** before you run it.

- **Proportion** (two groups): conversion or response rates; give the baseline rate and the smallest lift worth detecting, relative (10%) or absolute (2 points)
- **Mean** (two groups): averages such as basket value; give the standard deviation and the smallest difference
- **Survey** (one sample): estimate a proportion to a margin of error, with an optional finite population (a staff survey of 1,200 needs fewer responses)

Significance level, power, one or two-sided tests and unequal group sizes are options. With **daily traffic**, the block also says how many days the test needs to run.

Each row of the optional input is a **scenario** (columns matched by name: Scenario, Type, Baseline, Effect, Relative Effect, SD, Margin, Population, Alpha, Power, Sides, Ratio, Daily Traffic); anything a row does not give comes from the options. Without an input, the options describe one scenario.

Outputs: sample sizes per scenario, and a **power curve** for each two-group scenario. Pair with the A/B Test block to analyse the results afterwards.

## Language
Python

## Inputs
- **Input (optional)**: one row per planned test or survey (columns matched by name).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Scenario defaults | Type | `test_type` | Choice | Choices: Proportion (two groups); Mean (two groups); Survey margin of error. Default: Proportion (two groups). |
| Scenario defaults | Baseline (rate or mean) | `baseline` | Decimal number | For example 0.05 for a 5% conversion rate. Default: 0.05. |
| Scenario defaults | Smallest effect to detect | `effect` | Decimal number | Relative (0.1 = 10% lift) or absolute. Default: 0.1. |
| Scenario defaults | Effect is relative to the baseline | `relative_effect` | Tick box | Default: ticked. |
| Scenario defaults | Standard deviation (means) | `sd` | Decimal number | Default: 1.0. |
| Scenario defaults | Margin of error (survey) | `margin` | Decimal number | For example 0.03 for plus or minus 3 points. Default: 0.03. |
| Scenario defaults | Population size (survey, optional) | `population` | Decimal number | 0 = very large. Default: 0.0. |
| Scenario defaults | Daily traffic (optional) | `daily_traffic` | Decimal number | Visitors or customers per day across both groups. Default: 0.0. |
| Test settings | Significance level | `alpha` | Decimal number | Chance of calling a difference real when it is not; 0.05 is usual. Default: 0.05. |
| Test settings | Power | `power` | Decimal number | Chance of detecting the effect if it is there; 0.8 is usual. Default: 0.8. |
| Test settings | Test | `sides` | Choice | Two-sided detects a change in either direction; one-sided only the expected direction, and needs fewer records. Choices: Two-sided; One-sided. Default: Two-sided. |
| Test settings | Group 2 size relative to group 1 | `ratio` | Decimal number | 1 = equal groups. Default: 1.0. |

## Outputs
- **Sample sizes** (`sizes`): Per scenario: inputs, absolute and relative effect, sample size per group and total, days needed.
- **Power curve** (`power_curve`): Per two-group scenario: power at sample sizes from 10% to 200% of the required size.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
