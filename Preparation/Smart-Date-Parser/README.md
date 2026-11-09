# Smart Date Parser

Parses text fields holding dates in mixed formats (ISO, day-first or month-first, named months, compact, with time zones) into Date fields, and flags the values it could not read.

Dates collected from several suppliers, systems or spreadsheets rarely share one format: `2025-03-04`, `04/03/2025`, `5 March 2025`, `20250319` and `2025-03-10T08:50:00+01:00` can all sit in the same field. This block reads each value on its own and writes a Date field next to the original, with a true/false field marking the values that could not be read.

- **Formats read**: ISO dates and timestamps (with `T`, `Z` or an offset), slash, dash and dot dates (`04/03/2025`, `21-03-2025`), named months (`5 March 2025`, `March 12, 2025`, `7 Mar 2025 16:00`), compact `20250319`, plus any **custom formats** you give.
- **Day first**: ambiguous dates such as `04/03/2025` are read as 4 March when ticked, 3 April when not. A day above 12 (`13/03/2025`) can only be read one way and is. Values starting with a four-digit year (`2025-03-04`) are always year-month-day.
- **Complete dates only**: a value must hold a year, a month and a day. `March 2025`, `2025` or `12` fail and are flagged, rather than being completed with parts of the date the workflow runs.
- **Time zones**: values with a time zone or offset (`Z`, `+01:00`) are converted to UTC; values without one are kept as they are. The parsed fields have no time zone.
- **Order of attempts**: custom formats first, in the order given; then the general parser with your day-first setting, then with the other setting; then a list of common fixed formats.
- **Fields that are already Date fields** are copied unchanged. Whole-number fields such as `20250319` are read by their digits.

## Language and libraries

Python. It uses pandas (BSD 3-Clause licence) and python-dateutil (Apache 2.0 or BSD 3-Clause), both part of Omniscope's Python environment. Nothing else to install.

## Inputs
- **Input 1**: records with one or more fields holding dates as text.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Fields to parse | `fields_to_parse` | Fields | Text fields holding dates. Fields that are already Date fields are copied unchanged. From input 1. |
| Output suffix | `output_suffix` | Text | Added to each field name for the parsed field (`Order Date` becomes `Order Date_parsed`). A leading space is kept. Leave empty to replace the field in place. Default `_parsed`. |
| Day first | `prefer_day_first` | Yes/no | Read ambiguous dates such as `04/03/2025` as day/month (4 March). Unticked, month/day (3 April). Default: unticked. |
| Add failure flag | `add_failure_flag` | Yes/no | Add a field ending in `_failed`, true where a value was present but could not be read. Default: ticked. |
| Keep original fields | `keep_original_fields` | Yes/no | Keep the original text fields next to the parsed ones (only with an output suffix). Default: ticked. |
| Custom formats | `custom_formats` | Text | Optional. Python `strptime` codes, comma-separated, tried first; for example `%y%m%d,%d.%m.%Y`. |

## Outputs
- **Parsed** (`Output Data`): the input, with each parsed Date field after its original and, when the flag is on, a `_failed` field after it. Missing values stay missing and are not flagged.

## Limits
- Two-digit years follow the general parser's rule (`03` is 2003).
- Week numbers (`2025-W10`), quarters (`Q3 2025`) and day-of-year dates are not read unless a custom format covers them (`%Y/%j` for `2025/065`).
- The time-zone conversion uses the offset in the text only; local times without one are not converted.
- The `_failed` fields are true/false; Omniscope may show them as text.

## Size of input

The block streams the data in chunks and parses each distinct value once per chunk. In tests, 100,000 values took about 0.4 seconds when the dates repeat (two years of days) and about 2.4 seconds when every value is different.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
