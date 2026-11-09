# Sort fields

Reorders the fields of the data by name (case-insensitive, with numbers in names in numeric order: Q2 before Q10) or by type, optionally keeping chosen fields first.

Wide tables from surveys, pivots and system exports often arrive with their fields in no useful order. This block puts them in a predictable one, and keeps doing so when a later export adds or moves a field. Only the order of the fields changes; the records and their values are untouched.

- **By name**: alphabetical, ignoring case, with numbers compared by value: `Q1`, `Q2`, `Q3`, `Q10`, `Q11` (not `Q1`, `Q10`, `Q11`, `Q2`), and `apple` before `Banana`.
- **By type**: text fields first, then numbers (Integer and Decimal together), then dates, then yes/no fields; by name within each type.
- **Fields to keep first**: stay at the start, in the order chosen, whatever the sort; for example an ID or a name.

## Language and libraries

Python. It uses pandas (BSD 3-Clause licence), part of Omniscope's Python environment. Nothing else to install.

## Inputs
- **Input 1**: any records.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Sort fields by | `sortBy` | Choice | `name` (case-insensitive, numbers in numeric order) or `type` (text, numbers, dates, yes/no, then by name). Default: name. |
| Fields to keep first | `firstFields` | Fields | Optional. These fields stay at the start, in the order chosen. From input 1. |

## Outputs
- **Sorted** (`Output Data`): the input records with the fields in the new order.

## Limits
- Numbers in names are compared as whole numbers: `v1.10` sorts after `v1.9`, and a decimal point is not understood.
- Integer and Decimal fields are one group when sorting by type, so their order within it is by name.

## Size of input

The block streams the data; reordering is instant. In tests, 50,000 records with 200 fields took a quarter of a second.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
