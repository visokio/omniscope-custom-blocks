# Occupancy From Intervals

Occupancy over time from start and end times: average and peak concurrency per bucket, utilisation against capacity and time over capacity, per group.

Turns **start and end times** into **occupancy over time**: beds in a ward, cars in a car park, staff on site, concurrent users, rooms booked, machines running.

- Per group (ward, site, car park) and **time bucket** (15 minutes, hour, day): **average occupancy** (time-weighted), **peak occupancy**, arrivals and departures, and **utilisation** against a capacity
- Per group: the overall **peak** and when it was first reached, average occupancy and utilisation, **hours over capacity** and the median duration
- Capacity as one number or **per group** (`Ward A=24, Ward B=18`); an optional **weight** counts an interval as several (people in a booking)
- Intervals with no end are treated as still in progress at the **as-of** time

The calculation is exact (a sweep over every start and end), not a sample of time points.

## Language
Python

## Inputs
- **Input**: intervals with start and end times (and optional group and weight).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Intervals | Start time | `start_field` | Field | When each stay, booking or session began. From input 1. |
| Intervals | End time | `end_field` | Field | Empty = still in progress. From input 1. |
| Intervals | Group (optional) | `group_field` | Field | For example Ward or Car Park. From input 1. |
| Intervals | Weight (optional) | `weight_field` | Field | For example people in a booking. From input 1. |
| Intervals | As of (for open intervals) | `as_of` | Text | Default: the latest time in the data. |
| Occupancy | Time bucket | `bucket` | Choice | Length of each time slot the occupancy is measured in. Choices: Hour; 15 minutes; Day. Default: Hour. |
| Occupancy | Capacity | `capacity` | Decimal number | 0 = none. Default: 0.0. |
| Occupancy | Capacity by group | `capacity_by_group` | Text | For example: Ward A=24, Ward B=18 |

## Outputs
- **Occupancy** (`occupancy`): Per group and bucket: average and peak occupancy, arrivals, departures, capacity, utilisation, over capacity.
- **Summary** (`summary`): Per group: intervals, period, peak and when, average occupancy and utilisation, hours over capacity, median duration.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
