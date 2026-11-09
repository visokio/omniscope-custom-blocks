# As-Of Join

Joins each row to the record in force at its date (latest on or before, next, or nearest) per key, with a maximum gap and validity end dates.

Attaches to each row of input 1 the row of input 2 that was **in force at that row's date**, per key:

- the latest **exchange rate** on or before each transaction date (weekends and holidays use the last published rate)
- the **price list** or **tariff** effective at the order date
- the **owner, grade, address or status** valid at the time (slowly changing dimensions)

Options:
- **Direction**: latest on or before (default), next on or after, or nearest
- **Maximum gap** in days, so a rate that is months old does not count
- **End date** on input 2 for validity ranges (valid from / valid to)
- Which input 2 fields to bring across (default: all except keys and dates); names that clash get a suffix

Every input 1 row is kept, in its original order, with **As Of Date**, **Days From As Of Date** and **As Of Status** (Matched, No record in range, Expired, No date).

## Language
Python

## Inputs
- **Input 1**: the rows to enrich, with a date.
- **Input 2**: the dated reference table (effective date, optional end date).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Input 1 (rows) | Date field | `left_date` | Field | Date of each row in input 1, such as an invoice date. From input 1. |
| Input 1 (rows) | Key fields (optional) | `left_keys` | Fields | For example Currency or Product. Matched in order with the input 2 keys. From input 1. |
| Input 2 (dated reference table) | Effective date field | `right_date` | Field | Date from which each input 2 record applies, such as a rate date. From input 2. |
| Input 2 (dated reference table) | End date field (optional) | `right_end_date` | Field | Valid-to date, for validity ranges. From input 2. |
| Input 2 (dated reference table) | Key fields | `right_keys` | Fields | Default: the same names as input 1. From input 2. |
| Input 2 (dated reference table) | Fields to bring across (optional) | `fields_to_add` | Fields | Default: all except keys and dates. From input 2. |
| Matching | Direction | `direction` | Choice | Which reference record each row takes: the latest on or before its date, the next on or after, or the nearest. Choices: Latest on or before; Next on or after; Nearest. Default: Latest on or before. |
| Matching | Maximum gap (days) | `max_gap_days` | Decimal number | 0 = no limit. Default: 0.0. |
| Matching | Suffix for clashing names | `suffix` | Text | Default:  (as of). |

## Outputs
- **Joined** (`joined`): Input 1 with the fields from input 2, As Of Date, Days From As Of Date and As Of Status.
- **Summary** (`summary`): Rows per status, with the average and largest gap for matched rows.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
