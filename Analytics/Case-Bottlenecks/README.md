# Case Duration and Bottlenecks

From an event log: case durations and rework, the slowest and costliest handovers between activities, and activity statistics.

Measures processes from an **event log** (case, activity, timestamp): orders, claims, applications, tickets, patient visits.

- **Per case**: start, end, **duration**, steps, **rework** (an activity repeated), first and last activity, the **route** taken and how common that route is
- **Per handover** (activity A followed by activity B): how often it happens and how long it takes (median, average, 90th percentile, **total waiting**), ranked so the **slowest** and the **costliest** handovers come first
- **Per activity**: occurrences, cases, rework, median time until the next step, and how often it is the last step

Durations in hours or days. Events are ordered by time within each case, so the log can be in any order. Path Analysis shows the most common routes in more detail.

## Language
Python

## Inputs
- **Input**: an event log with case, activity and timestamp fields.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
|  | Case field | `case_field` | Field | Identifies a case, such as a claim, ticket or order number. From input 1. |
|  | Activity field | `activity_field` | Field | The name of the step recorded in each event. From input 1. |
|  | Timestamp field | `time_field` | Field | When the event happened; orders the events within each case. From input 1. |
|  | Durations in | `unit` | Choice | Unit for durations and waiting times. Choices: Hours; Days. Default: Hours. |
|  | Steps shown in a route | `max_variant_steps` | Whole number | Default: 12. |

## Outputs
- **Cases** (`cases`): Per case: start, end, duration, steps, rework, first and last activity, route, variant rank, slowest 10%.
- **Handovers** (`handovers`): Per pair of consecutive activities: count, cases, median / average / 90th percentile / total time, share of waiting, ranks.
- **Activities** (`activities`): Per activity: occurrences, cases, rework, median time to next step, times last step.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
