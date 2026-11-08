# Cohort Retention

Builds acquisition cohorts from activity or order data and measures retention and revenue per cohort over time, with an average retention curve.

Answers the questions every subscription, app and e-commerce business asks: *how many of the customers we won in March are still with us?* and *are newer customers sticking better than older ones?*

Each customer belongs to the **cohort** of the period (week, month, quarter, year) of their first activity. For each cohort and each later period the block counts the customers still active, so you get:

- the **cohort matrix** (long format, ready for a Pivot table or heat map): cohort, period number (0 = acquisition period), active customers, **retention %**, and if a revenue field is chosen, revenue, revenue per cohort customer and **cumulative revenue per customer** (a simple lifetime value curve)
- the **average retention curve** across cohorts (weighted by cohort size, and the plain mean of cohorts)
- a **customer table**: cohort, last active period, periods active, active in the latest period

Periods with no activity count as zero; recent cohorts simply have fewer periods. Input is any table with a customer and a date per activity or order.

## Language
Python

## Inputs
- **Input 1**: activity or order data with a customer field and a date field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Data | Customer field | `customer_field` | Field | Identifies a customer; the first date seen sets the cohort. From input 1. |
| Data | Activity or order date | `date_field` | Field | Date of each activity or order. From input 1. |
| Data | Revenue field (optional) | `revenue_field` | Field | Adds revenue, revenue per cohort customer and cumulative revenue per customer. From input 1. |
| Cohorts | Cohort period | `period` | Choice | Length of a cohort, and of each step along the retention curve. Choices: Month; Week (Monday to Sunday); Quarter; Year. Default: Month. |
| Cohorts | Periods to follow | `max_periods` | Whole number | How many periods after acquisition to track. Default: 24. |
| Cohorts | Text dates are day first | `day_first` | Tick box | Read 03/04/2025 as 3 April. Default: ticked. |

## Outputs
- **Cohort matrix** (`matrix`): Cohort x period number: active customers, retention, revenue, cumulative revenue per customer.
- **Retention curve** (`curve`): Average retention by period number across cohorts (weighted and mean).
- **Customer cohorts** (`customers`): Per customer: cohort, last active period, periods active, active in the latest period.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
