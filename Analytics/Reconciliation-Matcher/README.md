# Reconciliation Matcher

Matches two ledgers one-to-one on amount, reference and date with tolerances, plus group matches, and lists the unmatched items on each side.

Matches the items of two ledgers and lists what is left on each side: bank statement against cash book, invoices against payments, a supplier statement against the purchase ledger, card settlements against sales.

Matching runs in passes, each **one-to-one** and best match first:

1. **Exact**: same amount and same reference (references are compared ignoring spaces, punctuation and case), dates within the window
2. **Amount and date**: amount within the tolerance and dates within the window; the closest date wins, then the closest amount, then a matching reference
3. **Group**: several items with the same reference that add up to one item on the other side (one payment for three invoices, a deposit banked in two parts)

Fields that must agree (account, currency, company) restrict every pass. Side 2 amounts can be **sign-flipped** when one side records credits as negatives.

Outputs: both inputs with match status, match ID and rule, one row per match with the amounts and any difference, and a summary of matched and unmatched items and amounts.

## Language
Python

## Inputs
- **Input 1**: one side (for example the bank statement).
- **Input 2**: the other side (for example the cash book).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Input 1 | Amount | `amount_field_a` | Field | Amount of each item in input 1. From input 1. |
| Input 1 | Date (optional) | `date_field_a` | Field | Date of each item in input 1, for the date window. From input 1. |
| Input 1 | Reference (optional) | `reference_field_a` | Field | Reference or narrative in input 1, compared with input 2's. From input 1. |
| Input 2 | Amount | `amount_field_b` | Field | Amount of each item in input 2. From input 2. |
| Input 2 | Date (optional) | `date_field_b` | Field | Date of each item in input 2. From input 2. |
| Input 2 | Reference (optional) | `reference_field_b` | Field | Reference in input 2. From input 2. |
| Matching | Fields that must agree (optional) | `match_fields` | Fields | Same field names in both inputs, such as Account or Currency. From input 1. |
| Matching | Amount tolerance | `tolerance` | Decimal number | For example 0.01 for rounding differences. Default: 0.0. |
| Matching | Date window (days) | `date_window` | Decimal number | Maximum days between matched items. Default: 3.0. |
| Matching | Input 2 amounts | `sign` | Choice | Choose Opposite when one side records as negative what the other records as positive. Choices: Same sign as input 1; Opposite sign (flip). Default: Same sign as input 1. |
| Matching | Match groups with the same reference | `group_matching` | Tick box | One item against several that add up to it. Default: ticked. |

## Outputs
- **Input 1 items** (`side1`): Input 1 with Match Status, Match ID and Match Rule.
- **Input 2 items** (`side2`): Input 2 with Match Status, Match ID and Match Rule.
- **Matches** (`matches`): One row per match: rule, items and amount on each side, difference, date difference, references.
- **Summary** (`summary`): Matched and unmatched items and amounts per side, and matches per rule.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
