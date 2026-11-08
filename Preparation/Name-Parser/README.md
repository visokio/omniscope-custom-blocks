# Name Parser

Splits full names into title, first, middle, last and suffix, tidies capitalisation, flags organisations and builds salutations.

Splits full names into **title, first name, middle names, last name and suffix**, and builds **initials, a tidy name and a salutation** for mailings and matching.

- Handles titles (*Dr, Prof, Sir, Mx, Cllr, Rt Hon*...), suffixes and honours (*Jr, III, OBE, PhD*...), initials (*A. B. Patel*), and names written **Last, First** (*SMITH, JOHN*)
- Keeps surname particles with the surname (*van der Berg, da Silva, de la Cruz*)
- Optionally **tidies capitalisation**: *mcdonald* becomes *McDonald*, *o'brien* becomes *O'Brien*, hyphenated names keep both capitals
- Flags values that look like **organisations** (*Ltd, plc, LLP, Trust, & Sons*...) instead of splitting them
- Salutations: formal (*Dear Dr Smith-Jones*) or informal (*Dear Amelia*), falling back sensibly when parts are missing

A *Parse Note* explains unusual cases (single word, initial only, Last, First order). Names are hard; check the notes before a large mailing.

## Language
Python

## Inputs
- **Input**: data with a full-name field.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Full name field | `name_field` | Field | The whole name as one piece of text. From input 1. |
| Tidy capitalisation | `fix_case` | Tick box | Corrects all-capital or all-lower-case names, keeping forms such as McDonald and O'Brien. Default: ticked. |
| Salutation | `salutation_style` | Choice | Title and surname, or first name only. Choices: Formal (Dear Dr Smith); Informal (Dear Amelia). Default: Formal (Dear Dr Smith). |
| Greeting | `greeting` | Text | Default: Dear. |
| Prefix for new fields (optional) | `prefix` | Text |  |

## Outputs
- **Parsed names** (`parsed`): The input with Name Type, Title, First Name, Middle Names, Last Name, Suffix, Initials, Tidy Name, Salutation, Parse Note.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
