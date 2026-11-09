# Stratified Sample

Draws a reproducible random sample within strata: proportional with a minimum per stratum, equal, fixed number or percentage, with sampling weights and an allocation table.

Draws a random sample in which **every group (stratum) is represented**: regions, risk bands, customer segments, store formats. A simple random sample can miss small groups entirely; a stratified one cannot.

- **Proportional**: a total sample size split across strata in proportion to their size, with a **minimum per stratum** so small groups still get a few records (largest-remainder rounding, never more than a stratum holds)
- **Equal**: a total sample size split equally across strata
- **Fixed number per stratum**: for example 10 from each
- **Percentage per stratum**: for example 5% of each

Sampling is without replacement and **reproducible**: the same seed gives the same sample. Each sampled record gets a **Sample Weight** (stratum population / stratum sample size) for estimating population totals, and its stratum label. The **remainder** output holds the records not sampled (for train / test splits or control groups), and the **allocation** output shows population, sample size, fraction and weight per stratum.

## Language
Python

## Inputs
- **Input 1**: the population to sample from.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Strata | Strata fields | `strata_fields` | Fields | Sample within each combination of these fields. Leave empty for a simple random sample. From input 1. |
| Sample size | Allocation | `method` | Choice | How the sample is split between strata. Choices: Total sample, proportional to stratum size; Total sample, equal per stratum; Fixed number per stratum; Percentage per stratum. Default: Total sample, proportional to stratum size. |
| Sample size | Total sample size | `total_n` | Whole number | For proportional and equal allocation. Default: 100. |
| Sample size | Minimum per stratum | `min_per_stratum` | Whole number | Proportional allocation only: each stratum gets at least this many (or all its records, if fewer). Default: 1. |
| Sample size | Records per stratum | `per_stratum_n` | Whole number | For the fixed-number method. Default: 10. |
| Sample size | Percentage per stratum | `percent` | Decimal number | For the percentage method, 0 to 100. Default: 10.0. |
| Sample size | Random seed | `seed` | Whole number | The same seed always gives the same sample. Default: 42. |

## Outputs
- **Sample** (`sample`): Sampled records with Sample Weight and Stratum.
- **Not sampled** (`remainder`): All records not in the sample.
- **Allocation** (`allocation`): Per stratum: population, sample size, sampling fraction, weight, shares.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
