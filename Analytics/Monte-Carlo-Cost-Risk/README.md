# Monte Carlo Cost Risk

Simulates three-point estimates and risk events to give P10 / P50 / P80 / P90 totals, contingency, the probability of exceeding a budget, and the drivers of uncertainty.

Turns **three-point estimates** (low, most likely, high) for each line of a project estimate, budget, bid or forecast into a probability distribution of the total, by Monte Carlo simulation.

- Each line is sampled from a **PERT** (default), triangular or uniform distribution
- **Risk events** from a risk register occur with their probability (0-1 or %); lines with no probability always occur
- Optional **correlation** between lines (a single rank correlation, applied with the Iman-Conover method): treating lines as independent usually understates the risk
- **P10, P50, P80, P90, P95** of the total and of each group, the **contingency** needed above the base estimate for each confidence level, and the chance of exceeding the base or a target
- **Drivers**: which lines contribute most to the uncertainty (share of variance and rank correlation with the total), for a tornado chart
- The **S-curve** of the total (histogram with cumulative probability)

The base estimate is the sum of the most likely values of the lines that always occur. A fixed random seed makes runs repeatable.

## Language
Python

## Inputs
- **Input**: estimate lines with low, most likely and high values (and optional probability and group).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Estimate lines | Line name | `name_field` | Field | Names each estimate line or risk. From input 1. |
| Estimate lines | Low estimate | `low_field` | Field | Optimistic cost of the line. From input 1. |
| Estimate lines | Most likely estimate | `likely_field` | Field | Most likely cost of the line. From input 1. |
| Estimate lines | High estimate | `high_field` | Field | Pessimistic cost of the line. From input 1. |
| Estimate lines | Probability (optional) | `probability_field` | Field | For risk events; empty = always occurs. From input 1. |
| Estimate lines | Group (optional) | `group_field` | Field | For example work package. From input 1. |
| Simulation | Distribution | `distribution` | Choice | Shape of each line's range. PERT weights the most likely value; triangular gives more weight to the extremes. Choices: PERT; Triangular; Uniform (low to high). Default: PERT. |
| Simulation | Iterations | `iterations` | Whole number | Number of simulated totals. More gives steadier percentiles. Default: 10000. |
| Simulation | Correlation between lines | `correlation` | Decimal number | 0 = independent; 0.3 to 0.5 is common for related costs. Default: 0.0. |
| Simulation | Random seed | `seed` | Whole number | Fixes the random numbers, so a rerun gives the same results. Default: 1. |
| Simulation | Target or budget (optional) | `target` | Decimal number | Reports the chance of exceeding it. |
| Simulation | S-curve bins | `bins` | Whole number | Default: 50. |

## Outputs
- **Summary** (`summary`): Total and per group: base, mean, P10-P95, contingency to P50 / P80 / P90, probability over base (and target).
- **Drivers** (`drivers`): Per line: inputs, simulated mean, spread, P10 / P90, rank correlation with the total, share of variance, rank.
- **S-curve** (`distribution`): Histogram of the total with cumulative probability.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
