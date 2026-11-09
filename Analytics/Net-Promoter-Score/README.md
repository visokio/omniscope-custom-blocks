# Net Promoter Score

Net Promoter Score per group and period from 0-10 answers, with margin of error, confidence interval, weights, significance vs the rest and vs the previous period.

Calculates **Net Promoter Score** from 0 to 10 "how likely are you to recommend" answers, with the statistics usually left out of NPS dashboards.

- Promoters (9-10), passives (7-8) and detractors (0-6): counts and shares
- **NPS** = % promoters - % detractors, from -100 to +100
- **Margin of error and confidence interval**, so small groups are not over-read
- Optional **survey weights** (the effective sample size is used for the error)
- Per **group** (region, store, channel, agent): whether the group is significantly higher or lower than the rest
- Per **period** (month, quarter, year): the change from the previous period and whether it is significant

Blank answers and values that are not whole numbers from 0 to 10 (such as *Don't know*) are skipped and counted in the status message.

Outputs: the NPS table, the 0-10 score distribution per group, and the responses with their **NPS Category** and **NPS Points** (+100 / 0 / -100; the average of the points is the NPS, so it can be re-aggregated in any Report).

## Language
Python

## Inputs
- **Input**: survey responses with a 0-10 likelihood-to-recommend score.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Survey | Score field (0-10) | `score_field` | Field | The answer to the likelihood-to-recommend question, from 0 to 10. From input 1. |
| Survey | Group by (optional) | `group_fields` | Fields | For example Region or Channel. From input 1. |
| Survey | Weight field (optional) | `weight_field` | Field | Survey weights; leave empty for unweighted. From input 1. |
| Reporting | Date field (optional) | `date_field` | Field | Needed to report by period. From input 1. |
| Reporting | Report by period | `period` | Choice | Adds a row per period, compared with the period before. Needs a date field. Choices: None; Month; Quarter; Year. Default: None. |
| Reporting | Confidence level | `confidence` | Decimal number | For the margin of error and significance tests. Default: 0.95. |
| Reporting | Small sample below | `min_responses` | Whole number | Rows with fewer responses are flagged. Default: 30. |

## Outputs
- **NPS** (`nps`): Per group (and period): counts, shares, NPS, standard error, margin of error, confidence interval, vs rest, change vs previous period.
- **Score distribution** (`distribution`): Per group: responses and share for each score 0 to 10.
- **Responses** (`responses`): The input with NPS Category and NPS Points (+100 / 0 / -100).

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
