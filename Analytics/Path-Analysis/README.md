# Path Analysis

The most common event sequences per user or session, step-numbered transitions for Sankey charts, and next-step probabilities.

Finds the **most common sequences of events** per user or session (web pages, app screens, case or claim stages, patient pathways, machine states) and the **transitions** between steps.

- Events are ordered by time within each path; **repeated consecutive events** can be collapsed (*home > home > product* becomes *home > product*)
- Paths can **start** at the first occurrence of an event (for example *product*) and **stop** at the first of your **end events** (for example *purchase*)
- Paths are cut to a **maximum number of steps**, with *...* marking longer ones

Outputs:
- **Paths**: the top paths with counts, share, cumulative share, how many reach an end event and the median duration
- **Transitions**: step-numbered links (*1. home* to *2. product*), with *(exit)* where paths stop: ready for a Sankey chart
- **Next step**: the probability of each next event after each event (a Markov transition table), including leaving

## Language
Python

## Inputs
- **Input**: an event log with a user or session field, an event field and optionally a time field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Events | User or session field | `path_field` | Field | Identifies one path: all events with the same value form a sequence. From input 1. |
| Events | Event field | `event_field` | Field | The page, screen or step recorded in each event. From input 1. |
| Events | Time field (optional) | `time_field` | Field | Orders the events; without it, input order is used. From input 1. |
| Paths | Maximum steps | `max_steps` | Whole number | Paths are cut after this many steps, so long journeys group together. Default: 5. |
| Paths | Top paths | `top_n` | Whole number | 0 = all. Default: 50. |
| Paths | Collapse repeated consecutive events | `collapse_repeats` | Tick box | Treats the same event several times in a row (such as page reloads) as one step. Default: ticked. |
| Paths | Start at event (optional) | `start_event` | Text | Paths start at its first occurrence; paths without it are left out. |
| Paths | End events (optional) | `end_events` | Text | Comma-separated; a path stops at the first one, for example: purchase |

## Outputs
- **Paths** (`paths`): Top paths: rank, path, steps, count, share, cumulative share, first / last event, reached end event, median minutes.
- **Transitions** (`transitions`): Step-numbered From / To links with counts, for Sankey charts.
- **Next step** (`next_step`): From event, to event (or exit), transitions and probability.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
