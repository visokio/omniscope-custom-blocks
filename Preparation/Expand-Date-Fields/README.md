# Expand Date Fields

Adds year, quarter, month, week, day and day-name fields for each chosen date field, for filtering and grouping by part of a date without formulas.

Reports often need "orders by quarter", "deliveries on a Saturday" or "sales per ISO week". This block adds those parts as fields of their own, so a filter, a Pivot or a chart can use them directly.

- Choose one or more **date fields**. Each gets its own set of new fields, named after it: for `Order Date`, `Order Date_year`, `Order Date_month` and so on.
- The **time of day is ignored**: 31 March at 23:59 is still 31 March.
- Month and day names are **in English**, whatever the server's language.
- A **missing date** gives empty parts (the month start / end flags are empty too, not false).
- Weeks are **ISO weeks** (starting on Monday, week 1 holding the year's first Thursday). Each week comes with **its own ISO year**: Monday 29 December 2025 is in week 1 of 2026, so group by `_week_year` and `_weekofyear`, not by `_year` and `_weekofyear`.
- Every chosen field always gets all the new fields, even when it holds no dates, so the output's fields don't change with the data.

## Language
Python

## Inputs
- **Input 1**: records with one or more Date fields.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Date fields to expand | `dateFields` | Fields (date) | Each chosen field gets its own set of date-part fields, named after it. From input 1. |
| Time zones | `timezoneHandling` | Choice | How to read dates that carry a time zone other than UTC: **Keep local date and time** (the default; each date's own clock time and calendar date), **Convert to UTC** (a date just after midnight east of UTC moves to the day before), or **Stop if time zones are mixed**. Omniscope passes Date fields to the block in UTC, so for ordinary Date fields the three choices give the same result. |

## Outputs
- **Expanded** (`Output Data`): the input records with these fields added for each chosen date field `<field>`:

| Field | Type | Values |
|---|---|---|
| `<field>_year` | Integer | Calendar year |
| `<field>_month` | Integer | 1 to 12 |
| `<field>_month_name` | Text | January to December |
| `<field>_day` | Integer | Day of the month, 1 to 31 |
| `<field>_day_name` | Text | Monday to Sunday |
| `<field>_dayofyear` | Integer | 1 to 366 |
| `<field>_quarter` | Integer | 1 to 4 (calendar quarters) |
| `<field>_is_month_start` | Boolean | True on the 1st of the month |
| `<field>_is_month_end` | Boolean | True on the last day of the month |
| `<field>_weekofyear` | Integer | ISO week, 1 to 53 |
| `<field>_week_year` | Integer | The ISO year the week belongs to |

## Limits

- Quarters are calendar quarters; there is no option for a financial year starting in another month.
- A field already named like a new one (for example `Order Date_year`) is overwritten.
- In tests, 1,000,000 records were expanded in under 3 seconds.

## Dependencies
None beyond pandas, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
