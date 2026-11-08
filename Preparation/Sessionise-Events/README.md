# Sessionise Events

Groups each user's timestamped events into sessions by an inactivity gap, adding session IDs to events and producing a session summary with duration, landing and exit events.

Turns a raw stream of timestamped events (web or app clicks, machine log lines, card transactions, door entries) into **sessions**, the way web analytics tools do: for each user or device, a new session starts when the gap since their previous event is longer than a timeout (30 minutes by default) or, optionally, when a session reaches a maximum length.

**Events output**: every input row with *Session ID*, *Session Number* (per user), *Event Number In Session*, *Seconds Since Previous Event* and *Is Session Start*.

**Sessions output**: one row per session with start, end, duration, number of events, first event (landing page) and last event (exit page), total value (such as order value) and a bounce flag (one-event sessions).

Events can arrive in any order; they are sorted by user and time. Rows without a user or a valid timestamp are kept in the events output without a session.

## Language
Python

## Inputs
- **Input 1**: timestamped events with a user or device field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Events | User or device field | `user_field` | Field | Who the events belong to: visitor ID, device, card number, badge. From input 1. |
| Events | Timestamp field | `time_field` | Field | Date and time of each event. From input 1. |
| Events | Event name field (optional) | `event_field` | Field | Page, screen or event type; gives the first and last event of each session. From input 1. |
| Events | Value field (optional) | `value_field` | Field | Summed per session, such as order value. From input 1. |
| Sessions | Inactivity gap (minutes) | `gap_minutes` | Decimal number | A gap longer than this starts a new session. 30 is the web analytics convention. Default: 30.0. |
| Sessions | Maximum session length (hours) | `max_session_hours` | Decimal number | Optional: split sessions longer than this. 0 = no limit. Default: 0.0. |
| Sessions | Text dates are day first | `day_first` | Tick box | Read 03/04/2025 as 3 April. Default: ticked. |

## Outputs
- **Events with sessions** (`events`): Input events with Session ID, Session Number, Event Number In Session, Seconds Since Previous Event, Is Session Start.
- **Sessions** (`sessions`): One row per session: user, start, end, duration, events, first and last event, total value, bounce.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
