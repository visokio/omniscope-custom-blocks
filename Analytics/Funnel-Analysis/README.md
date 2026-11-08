# Funnel Analysis

Builds conversion funnels from event data: users reaching each ordered step within an optional time window, conversion, drop-off and time between steps, per segment.

Measures a conversion funnel from raw event data: how many users reach each step (for example *view product, add to basket, begin checkout, purchase*), where they drop off, and how long each step takes.

- Steps are listed in order; event names are matched ignoring case. Other events are ignored.
- **In order**: a step only counts if it happens after the user reached the previous step (untick to count any order)
- Optional **time window**: every step must happen within N hours of the user's first step (for example 48 hours)
- **Segments** such as device or channel (taken from each user's first event) give one funnel per segment

**Funnel output**, per segment and step: users, conversion from the start, conversion from the previous step, drop-off and the median hours from the previous step.
**Users output**: one row per user with the furthest step reached, whether they converted, each step's time and hours to convert, for remarketing lists or deeper analysis.

## Language
Python

## Inputs
- **Input**: an event log with a user ID, an event name and a timestamp.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Events | User field | `user_field` | Field | Identifies the person or session moving through the funnel. From input 1. |
| Events | Event name field | `event_field` | Field | Holds the event names listed in the funnel steps. From input 1. |
| Events | Event time field | `time_field` | Field | When each event happened. From input 1. |
| Events | Segment by (optional) | `segment_fields` | Fields | For example Device or Channel. From input 1. |
| Funnel | Funnel steps, in order | `steps` | Text | Event names separated by commas or ->, for example: view_product, add_to_basket, begin_checkout, purchase |
| Funnel | Steps must happen in order | `ordered` | Tick box | Ticked: a step counts only after the previous one. Unticked: any order. Default: ticked. |
| Funnel | Time window (hours) | `window_hours` | Decimal number | All steps within this many hours of the first step. 0 = no limit. Default: 0.0. |

## Outputs
- **Funnel** (`funnel`): Per segment and step: users, conversion from start and previous step, drop-off, median hours from previous step.
- **Users** (`users`): Per user: segment, steps reached, furthest step, converted, step times, hours to convert.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
