# Churn Survival Curves

Kaplan-Meier retention curves with censoring, confidence bands, median lifetime, milestone retention and log-rank tests between groups.

**Kaplan-Meier retention curves** from start and end dates: customers, subscriptions, contracts, members, employees, machines. Customers who are still active are counted correctly as *censored* instead of being dropped or treated as churned.

- **Retention** at each point in time with a **confidence band** (Greenwood variance, log-log interval), with the numbers at risk, ended and censored
- **Median lifetime** with its confidence interval, **retention at milestones** you choose (for example 3, 6, 12 and 24 months) and the **restricted mean lifetime** up to a common horizon
- Per **group** (plan, channel, region, cohort): **log-rank tests** across all groups and of each group against the rest

Use start and end dates (an empty end date means still active at the *as of* date), or a duration field with an optional event flag. An optional event field marks which endings count (for example only cancellations, not upgrades).

Python, no extra packages. The public R *Survival* block offers Kaplan-Meier and Fleming-Harrington curves; this block adds the churn-oriented summaries and log-rank tests.

## Language
Python

## Inputs
- **Input**: one row per customer or subscription, with start and end dates (or a duration and event flag).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Lifetimes | Start date | `start_field` | Field | Date each customer or subscription started. From input 1. |
| Lifetimes | End date | `end_field` | Field | Empty = still active. From input 1. |
| Lifetimes | Or a duration field | `duration_field` | Field | Instead of dates, in the unit below. From input 1. |
| Lifetimes | Event field (optional) | `event_field` | Field | Yes / true / 1 = ended (churned). Other values are censored. From input 1. |
| Lifetimes | Compare groups (optional) | `group_field` | Field | For example Plan or Channel. From input 1. |
| Lifetimes | As of date (optional) | `as_of` | Text | Default: the latest date in the data. |
| Reporting | Time unit | `unit` | Choice | Unit for lifetimes, the curve and the milestones. Choices: Months; Weeks; Days; Years. Default: Months. |
| Reporting | Retention milestones | `milestones` | Text | In the time unit, for example: 3, 6, 12, 24 Default: 3, 6, 12, 24. |
| Reporting | Confidence level | `confidence` | Decimal number | Default: 0.95. |

## Outputs
- **Curve** (`curve`): Per group and time: at risk, ended, censored, retention, confidence band, churned share.
- **Summary** (`summary`): Per group: customers, ended, censored, median lifetime and CI, retention at milestones, restricted mean, log-rank vs rest.
- **Tests** (`tests`): Log-rank test across all groups.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the Survival Analysis block

The community **Survival Analysis** block (R) draws Kaplan-Meier curves with the R survival package. Use this block when you also want median lifetimes per group, retention at chosen milestones and log-rank tests, without installing R packages.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
