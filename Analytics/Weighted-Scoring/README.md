# Weighted Scoring

Multi-criteria scorecards: normalise criteria, apply weights, rank alternatives, apply must-pass thresholds and test how sensitive the winner is to the weights.

A **multi-criteria scorecard** for choosing between alternatives: suppliers in a tender, sites for a new store, bids, projects, candidates.

- Each criterion is put on a **0-100 scale** (min-max, percent of best, rank or z-score); price, distance, risk and other *lower is better* criteria are turned round
- **Weights** are multiplied in and summed to a 0-100 total; alternatives are **ranked**, within groups if chosen (for example per lot)
- Optional **thresholds** (minimum and maximum per criterion) knock out alternatives that fail a must-have, with the reason
- Missing values score as worst, as average, or the weights are spread over the criteria the alternative has
- **Sensitivity**: for each criterion, how far its weight would have to move to change the leader, and who would lead instead

Weights can be typed in (for example `Price: 35, Quality: 25, Lead time: 10`) or come from a **criteria table on input 2** with one row per criterion: name, weight, and optionally direction (*Higher* / *Lower*), minimum and maximum.

Outputs: scores and ranks per alternative, the criteria with weights and sensitivity, and the points per alternative and criterion in long form for stacked bar charts.

## Language
Python

## Inputs
- **Input 1**: the alternatives, one row each, with a numeric field per criterion.
- **Input 2 (optional)**: criteria table: name, weight, direction, minimum, maximum.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Alternatives (input 1) | Alternative name field | `name_field` | Field | Names each option being scored, such as a supplier. From input 1. |
| Alternatives (input 1) | Criteria fields | `criteria_fields` | Fields | Numeric fields to score on. Not needed when input 2 lists the criteria. From input 1. |
| Alternatives (input 1) | Lower is better | `lower_better_fields` | Fields | Criteria where a lower value is better, such as price or risk. From input 1. |
| Alternatives (input 1) | Rank within (optional) | `group_fields` | Fields | For example a lot or category. From input 1. |
| Scoring | Weights | `weights` | Text | 'Field: weight' pairs, or numbers in criteria order. Empty = equal weights. Weights are scaled to sum to 100%. |
| Scoring | Normalisation | `method` | Choice | How each criterion is put on a common 0 to 100 scale before weighting. Choices: Min-max (worst 0, best 100); Percent of best; Rank; Z-score (mean 50). Default: Min-max (worst 0, best 100). |
| Scoring | Missing values | `missing` | Choice | How an option with no value for a criterion is scored. Choices: Score as worst (0); Score as average (50); Spread weight over available criteria. Default: Score as worst (0). |
| Criteria table (input 2, optional) | Criterion name | `crit_name_field` | Field | Must match a field of input 1. From input 2. |
| Criteria table (input 2, optional) | Weight | `crit_weight_field` | Field | Weight of each criterion; scaled to sum to 100%. From input 2. |
| Criteria table (input 2, optional) | Better when (Higher / Lower) | `crit_direction_field` | Field | Higher or Lower: which way is better for the criterion. From input 2. |
| Criteria table (input 2, optional) | Minimum (must pass) | `crit_min_field` | Field | Lowest acceptable value; options below it fail. From input 2. |
| Criteria table (input 2, optional) | Maximum (must pass) | `crit_max_field` | Field | Highest acceptable value; options above it fail. From input 2. |

## Outputs
- **Scores** (`scores`): Per alternative: 0-100 score and weighted points per criterion, total, thresholds passed, rank, gap to leader.
- **Criteria** (`criteria`): Per criterion: weight, share, direction, thresholds, averages and the weight change that would change the leader.
- **Contributions** (`contributions`): Long form: alternative, criterion, points; for stacked bar charts.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
