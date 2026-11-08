# Duplicate Survivorship

Finds duplicates within a dataset on several match keys, keeps a survivor per group by rules and fills its gaps from the duplicates.

Finds **duplicate records within one dataset** and keeps the **best record** of each group, the way data stewards de-duplicate customer, supplier and product masters.

- **Match keys** tried in order, for example `Email; Name + Postcode; Phone`: records agreeing on any key (after ignoring case, spaces and punctuation) join the same group, and groups chain together
- Fields can be compared on **digits only** (phone numbers, VAT numbers)
- **Survivor rules**: most complete record, latest or earliest date, highest or lowest value, then first in the input
- Optionally **fills gaps** in the survivor from the other records in its group, and says which fields were filled

Outputs: every record with group, group size, survivor flag and the key that linked it; the de-duplicated table; and one row per duplicate group. For approximate matching (typos), run Fuzzy Match first.

## Language
Python

## Inputs
- **Input**: the records to de-duplicate.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Match keys | `match_keys` | Text | Keys separated by ';', fields within a key by '+', for example: Email; Name + Postcode |
| Compare on digits only | `digits_only_fields` | Fields | For example Phone. From input 1. |
| Keep | `survivor_rule` | Choice | Which record in each duplicate group is kept. Choices: Most complete record; Latest by a date; Earliest by a date; Highest by a value; Lowest by a value. Default: Most complete record. |
| Date or value for the rule | `rule_field` | Field | The date or number the Keep rule looks at, such as Last Updated. From input 1. |
| Fill gaps in the survivor from its duplicates | `fill_gaps` | Tick box | Empty fields in the kept record take a value from its duplicates. Default: ticked. |

## Outputs
- **Records** (`records`): Every record with Duplicate Group, Group Size, Survivor, Linked By and Filled Fields.
- **Survivors** (`survivors`): One record per group (the de-duplicated table), with records merged and fields filled.
- **Groups** (`groups`): Per duplicate group: records, survivor row, keys that linked them.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the core De-duplicate block

Use the core **De-duplicate** block to keep one record from each set of exact duplicates. Use this block when the survivor has to be chosen by rules (most recent, most complete, highest or lowest value) and its gaps filled from the other duplicates.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
