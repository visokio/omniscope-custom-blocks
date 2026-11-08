# Time Duration Unit Converter

Turns times of day and durations into a number of milliseconds, seconds, minutes or hours, in a new field for each chosen field, ready to add up, average or compare.

Call logs, timesheets, race results and machine logs record durations as text (`0:04:35`, `12 min`, `1h 5m`) and times as dates (`2025-05-12 08:31:15`). Neither can be summed, averaged or compared with a target until it is a plain number. This block adds a number field for each chosen field, in the unit you choose.

- **Date fields** give the **time since midnight**; the date itself is ignored. `2025-05-12 08:31:15` is 511.25 minutes, and so is the same time on any other day.
- **Text fields** are read as durations. Accepted forms include:
  - clock style: `0:04:35`, `1:45:20.5`, `08:30` (two parts are **hours and minutes**: `6:30` is 6 hours 30 minutes; write 6 minutes 30 seconds as `0:06:30`);
  - with days: `1 day 02:00:00`;
  - with units: `12 min`, `45 s`, `2 hours`, `1h 5m`, `90 minutes`;
  - ISO 8601: `PT18M`, `PT1H30M`.
- **Text that can't be read is left empty**, and the block's message says how many values that was in each field (`about 10 min`, a bare `3` with no unit).
- **New field names** are the field's name with the unit added: `Handling time_m` for minutes, `Started_s` for seconds (`_ms`, `_s`, `_m`, `_h`). An input field with that name already is replaced.
- **Missing values stay missing.** Negative durations (`-0:30`) give negative numbers.

## Language and libraries

Python. It uses pandas (BSD 3-Clause licence), part of Omniscope's Python environment. It needs nothing else installed.

## Inputs
- **Input 1**: records with one or more Date or text fields.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Fields to convert | `date_fields` | Fields (Date, text) | Date fields (time since midnight) or text fields holding durations or times. From input 1. |
| Unit | `unit` | Choice | Milliseconds, Seconds, Minutes or Hours (`ms`, `s`, `m`, `h`): the unit of the new fields. Default: Seconds. |

## Outputs
- **Converted** (`Output Data`): the input records with a new number field for each chosen field.

## Limits
- **Dates give the time of day, not the time between two dates.** To measure from one date to another, use `DATEDIFF` in a formula.
- **Number fields are not accepted**: the block can't know whether 90 means seconds or minutes. Divide or multiply in a formula instead.
- **Two-part times are hours and minutes.** Minutes and seconds such as lap times written `6:30` need a leading `0:`.
- The time of day is taken from the date as it reaches the block. Omniscope passes dates to Python in UTC; for dates recorded without a time zone this is the time shown in the data.
- Only the English unit names and abbreviations pandas knows are read: `2 hrs` and `3 Std.` are not.

## Size of input

Each distinct text is read once. In tests, 200,000 records with a date field and a text field (86,000 different durations) took under a second.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
