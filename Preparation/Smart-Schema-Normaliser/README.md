# Smart Schema Normaliser

Cleans up an export with untidy field names: makes the names lower case with underscores, merges fields whose names differ only in case, spaces or dashes, and gives each text field a number, date, yes/no or text type, working through the data in chunks so large inputs never have to fit in memory.

Data appended from two systems, or exported by hand over the years, often has the same field twice under slightly different names (`Customer ID` and `customer_id`), numbers and dates held as text, and yes/no answers written several ways. This block tidies all of it in one step, without a list of fields to configure.

- **Names**: each field name is trimmed, made lower case, and runs of spaces, dashes and underscores become one underscore. `Sign-up Date` becomes `sign_up_date`, `Monthly Spend` becomes `monthly_spend`. Other characters are kept (`Amount (£)` becomes `amount_(£)`), and camel case is not split (`CustomerID` becomes `customerid`).
- **Merging**: fields whose names become the same are merged into one, taking the first field's value, or the next field's where it is missing. With **Prefer non-empty values**, empty text counts as missing too.
- **Types**: each text field gets the first type that fits at least the **Auto cast threshold** share of its values (default 0.98; missing values are not counted): number (Integer when every value is whole, Decimal otherwise), date, yes/no, or else text. The values that don't fit the chosen type become empty.
- **Safeguards**: text with a leading zero (`00123`, a code or an ID) stays text; text counts as a date only when it looks like one (`2024-03-02`, `04/03/2024`, `4 March 2024`, `March 4, 2024`). Yes/no means `true/false`, `yes/no`, `y/n`, `t/f` or `1/0`, in any case (a field of only `1` and `0` is a number field).
- **Day first**: ambiguous dates such as `04/03/2024` are 4 March when ticked, 3 April when not. Dates starting with a four-digit year are always year-month-day. Dates with an offset are converted to UTC.
- **Fields that already have a type** (Integer, Decimal, Date) are kept as they are.
- **Types are decided from the first chunk.** The block streams: Omniscope passes the records through in chunks of 10,000, and every chunk must be written with the same field types. So each text field's type is decided from the first chunk and kept for the rest. A later value that doesn't fit (`lots` in a number field, `2.5` in a field the first chunk made Integer, `soon` in a date field) becomes empty, and the block's message counts these values per field: `Values that didn't fit their field's type (now empty): orders 2`. A field that is empty throughout the first chunk stays text.
- **Missing values** stay missing, unless you set a default for numbers, dates or text.

## How it relates to other blocks

The core **Format field names** block changes how field names are written, and **Define schema** or **Field organiser** set names and types from a list you keep in the block; neither guesses types from the values. Use **Define schema** when you know the schema. The community **Canonical Schema Mapper** maps aliases to names you choose, from rules kept as data.

## Language and libraries

Python. It uses pandas (BSD 3-Clause licence), part of Omniscope's Python environment. Nothing else to install.

## Inputs
- **Input 1**: any records. The block is most useful when the File block's type detection is left on for the clean fields, or turned off so this block decides every type.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Prefer non-empty values | `prefer_non_empty_strings` | Yes/no | When merging fields, empty text is replaced by the next field's value, like a missing value. Default: ticked. |
| Sort fields by name | `sort_columns` | Yes/no | Order the output fields alphabetically. Unticked, they keep the order in which they first appear. Default: unticked. |
| Auto cast threshold | `auto_cast_threshold` | Number | Share of a field's values (0 to 1, missing not counted) that must fit a type for the field to get it. Default 0.98. |
| Day first | `day_first` | Yes/no | Read `04/03/2024` as 4 March. Default: unticked (3 April). |
| Default for missing numbers | `number_default` | Text | Optional. A number (such as `0`) put in empty values of number fields. Empty: they stay missing. |
| Default for missing dates | `datetime_default` | Text | Optional. A date, such as `1970-01-01`, put in empty values of date fields. |
| Default for missing text | `string_default` | Text | Optional. Put in empty values of text fields. |

## Outputs
- **Normalised** (`Output Data`): one record per input record, with one field per distinct normalised name.

## Limits
- Numbers must be plain (`1234.5`, `-0.25`, `1e3`); thousands separators and currency signs (`1,234`, `£12`) keep a field as text.
- The type is decided from the first 10,000 records. If the start of the input isn't typical (a field that only fills in later, whole numbers first and fractions later), sort or filter before this block, or set the type afterwards with a Field Organiser.
- A field whose values are all missing keeps its type.
- Yes/no fields show as text `True`/`False` in Omniscope (checked on a server).

## Size of input

The block streams, so it holds one chunk at a time. On an Omniscope server, 300,000 records with five text fields (IDs, whole numbers, ISO dates, yes/no, decimals) took 15 to 30 seconds, with the three values planted after the first chunk that didn't fit their types counted and left empty.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
