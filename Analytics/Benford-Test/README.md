# Benford's Law Test

Tests whether amounts follow Benford's law (first, first-two or second digit), overall or per group, with chi-square, MAD conformity and flagged records for follow-up.

In many real-world sets of amounts (invoices, expenses, payments, claims, populations) about 30% of values start with 1 and under 5% with 9: **Benford's law**. Invented or manipulated figures usually do not follow it, so a deviation is a well-established *screening* signal for auditors and fraud teams. It is not proof: some data legitimately does not follow Benford (prices set by policy, capped amounts, assigned numbers).

- **First digit** test (1 to 9), **first two digits** (10 to 99, sharper, needs more data) or **second digit** (0 to 9)
- Overall or **per group**: department, supplier, employee, cost centre
- Per digit: observed vs expected share and a z-statistic (with continuity correction); over- and under-represented digits flagged
- Per group: **chi-square** and p-value, **mean absolute deviation (MAD)** with Nigrini's conformity bands (*Close*, *Acceptable*, *Marginally acceptable*, *Nonconformity*). Because MAD bands assume large samples, a group is only called *Nonconformity* when the chi-square test is also significant; the expected MAD for a conforming group of that size is shown for comparison
- The **records** behind the over-represented digits of nonconforming groups, ready for follow-up

Amounts below a minimum (default 10) are ignored, as is usual for first-digit tests; negative amounts are tested on their absolute value. Pure Python: no packages needed.

## Language
Python

## Inputs
- **Input 1**: records with an amount field (invoices, expenses, payments, claims).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Data | Amount field | `value_field` | Field | The amounts to test, such as invoice or expense values. From input 1. |
| Data | Test separately for each (optional) | `group_fields` | Fields | For example Department, Supplier or Employee. From input 1. |
| Test | Test | `test` | Choice | Which digits to compare with Benford's law. First two digits is the finer test usually used in audit. Choices: First digit (1-9); First two digits (10-99); Second digit (0-9). Default: First digit (1-9). |
| Test | Ignore amounts below | `min_value` | Decimal number | Small amounts distort first-digit tests; 10 is the usual floor. Default: 10.0. |
| Test | Minimum values per group | `min_records` | Whole number | Groups with fewer values get no conformity verdict. Default: 100. |
| Test | Significance for nonconformity | `p_threshold` | Decimal number | A group is only called nonconforming when its MAD is in the nonconformity band and the chi-square p-value is below this. Default: 0.01. |
| Test | Z threshold for flagging digits | `z_threshold` | Decimal number | 1.96 is about 95% confidence; 2.57 about 99%. Default: 1.96. |

## Outputs
- **Digit distribution** (`digits`): Per group and digit: count, observed and expected share, difference, z-statistic, flag.
- **Conformity summary** (`summary`): Per group: values tested, chi-square, p-value, MAD, conformity verdict, over-represented digits.
- **Flagged records** (`flagged`): Input records whose tested digits are over-represented in a nonconforming group.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
