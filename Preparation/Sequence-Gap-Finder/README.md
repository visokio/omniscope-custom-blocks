# Sequence Gap Finder

Finds missing, duplicate and out-of-order numbers in invoice, cheque or ticket sequences, per series, with a completeness summary.

Checks numbered documents (invoices, credit notes, cheques, purchase orders, tickets) for **missing numbers**, **duplicates** and numbers **issued out of date order**, per series: the completeness test auditors run on document sequences.

- Numbers can carry a prefix (*INV-000123*): the digits at the end are the sequence number and the rest is the series, unless you give a series field
- Gaps are listed with the missing numbers (up to a limit per gap), formatted like the originals
- With a date field, documents dated earlier than a lower-numbered document are flagged
- Summary per series: first and last number, expected count, missing, gaps, duplicates, out of order and completeness

## Language
Python

## Inputs
- **Input**: documents with a number field (and optional series and date).

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Document number field | `number_field` | Field | The document number, with or without a text prefix. From input 1. |
| Series field (optional) | `series_field` | Field | Default: the text before the digits. From input 1. |
| Document date (optional) | `date_field` | Field | For the date order check. From input 1. |
| Missing numbers listed per gap | `max_missing_listed` | Whole number | A longer gap lists this many numbers and then '...'. Default: 20. |

## Outputs
- **Gaps** (`gaps`): Per gap: series, last number before, first after, missing count, missing numbers.
- **Problems** (`problems`): Per problem document: duplicate number or dated before an earlier number.
- **Summary** (`summary`): Per series: documents, first and last number, expected, missing, gaps, duplicates, out of order, completeness.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
