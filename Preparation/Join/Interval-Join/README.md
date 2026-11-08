# Interval Join

Joins each record of the first input to the intervals in the second input that contain its value (a number or a date between a start and an end), optionally only where another field matches as well.

An ordinary join pairs records whose key values are equal. Many lookups are by range instead: a parcel's weight falls in a price band, an order's date in a price period, an exam score in a grade boundary, a reading in an alert level. The second input holds the intervals, one per record, with a start and an end; the block pairs each first-input record with every interval that contains its value.

How a record is matched:

- **Value, start and end** must all be numbers, or all dates. A value equal to the start or the end is inside the interval or not according to the **Start** and **End** options; the defaults (start inclusive, end exclusive) suit bands that follow on from each other, such as 0 to 2, 2 to 5, 5 to 10, where 2 belongs to the second band only.
- **An empty start** means the interval has no lower limit, and **an empty end** no upper limit ("10 kg and over").
- **Also match on**: choose a field in each input that must be equal too, for example a delivery zone, so each zone is matched only against its own bands. Records with an empty value in that field match nothing.
- **Overlapping intervals**: a value inside several intervals gives one output record for each.
- **Join type**: **Inner** keeps only records whose value falls in an interval. **Left** keeps every first-input record; those in no interval (or with an empty value) have empty fields from the second input.

Things to know:

- Output order: the first input's order; a record matching several intervals is followed by them in the second input's order.
- The output has the first input's fields, then the second input's. A field name in both inputs gets `.1` on the second input's copy (`Zone` and `Zone.1`).
- An interval whose end is before its start never matches; the block's message counts them.
- Fields keep their types: dates stay dates, whole numbers stay whole numbers.
- Text fields can't be used as the value, start or end: convert numbers held as text first (for example with a Field Organiser).

## Language and libraries

Python, using pandas (BSD 3-Clause) and numpy (BSD 3-Clause), both part of Omniscope's Python environment. Nothing else to install. (Earlier versions used the pandasql package; it is no longer needed.)

## Inputs
- **Input 1**: records with the value to look up (a number or a date).
- **Input 2**: the intervals, one per record, with a start and an end field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Interval join | Join type | `join_type` | Choice | Inner (`INNER`, default) or Left (`LEFT`). |
| Interval join | Value in interval (first input) | `value` | Field | The number or date field to look up. From input 1. |
| Interval join | Interval start (second input) | `start` | Field | Where each interval starts. Empty means no lower limit. From input 2. |
| Interval join | Interval end (second input) | `end` | Field | Where each interval ends. Empty means no upper limit. From input 2. |
| Interval join | Start | `start_comparator` | Choice | Inclusive (`>=`, default) or Exclusive (`>`): whether a value equal to the start is inside. |
| Interval join | End | `end_comparator` | Choice | Inclusive (`<=`) or Exclusive (`<`, default): whether a value equal to the end is inside. |
| Also match on (optional) | Field in first input | `left` | Field | A field that must also be equal. From input 1. |
| Also match on (optional) | Field in second input | `right` | Field | The matching field of input 2. Choose both or neither. |

## Outputs
- **Joined** (`Output Data`): each first-input record once per interval containing its value, with the interval's fields; in a Left join, also the records in no interval, with empty interval fields.

## Size of input

The intervals are sorted and each value is compared only with the intervals near it, so bands that follow on from each other are fast: 200,000 values against 1,000 bands took about 0.1 seconds in tests. Many overlapping intervals (or wide ones that contain most values) produce one output record per match, and the output, time and memory grow with it.

## Source
[script.py](script.py)

The sample data in `sample-data/` (parcels and a delivery tariff) is invented.
