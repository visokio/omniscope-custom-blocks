# Melt De-pivot

Keeps the chosen fixed fields and turns every other field into records: one record per input record and field, with the field's name and its value. Values of different types become text.

Data often arrives wide: a column per month, per survey question or per measurement. Charts, aggregates and filters are easier on long data, with the month (or question) in one field and the value in another. This block "melts" the wide table: choose the fields to keep as they are, and every other field becomes a pair of name and value.

For example, Store, Region, Jan, Feb, Mar, Apr with Store and Region fixed becomes Store, Region, Field, Value: four records per store.

How it works:

- **Fixed fields** are copied onto every output record. Every field that is not fixed is de-pivoted. With no fixed fields, every field is de-pivoted.
- Each input record's values come out together, in the order of the fields (all of the first store's months, then the next store's).
- **Types**: if the de-pivoted fields are all of one type (all numbers, all dates, all text), the value field keeps it; whole numbers stay whole numbers. If they are of different types, every value is turned into text, so nothing changes type silently: whole numbers without decimals ("10", not "10.0"), dates as `2026-01-31` (with the time, `2026-01-31 08:30:00`, when any value has one). The block's message says when this happened.
- **Leave out empty values**: skips records whose value is empty (a sparse table with many blank cells gives far fewer records).

Things to know:

- The two new field names must differ from each other and from the fixed fields; the block stops with a message otherwise.
- Omniscope's core **De-pivot** block does the same job, with rule-based field selection, and needs no Python. Use this block when you want its handling of mixed types or empty values, or a script to adapt.

## Language and libraries

Python, using pandas (BSD 3-Clause) and numpy (BSD 3-Clause), both part of Omniscope's Python environment. Nothing else to install.

## Inputs
- **Input 1**: a wide table.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Fixed fields | Fixed fields | `fixed_fields` | Fields | Fields kept on every output record. Every other field is de-pivoted. From input 1. |
| New fields | Name field | `var_name` | Text | Name of the new field holding the de-pivoted field's name. Default: Field. |
| New fields | Value field | `value_name` | Text | Name of the new field holding the value. Default: Value. |
| New fields | Leave out empty values | `drop_empty` | Yes/no | Skip records whose value is empty. Default: not ticked. |

## Outputs
- **De-pivoted** (`Output Data`): one record per input record and de-pivoted field: the fixed fields, then the name field and the value field.

## Size of input

The output has (records) x (de-pivoted fields) records. 100,000 records with 12 fields to de-pivot (1.2 million records out) took about a quarter of a second in tests.

## Source
[script.py](script.py)

The sample data in `sample-data/store-sales-wide.csv` is invented.
