# Fuzzy Match

Finds near-duplicate records within one input (with group IDs), or the best matching record in a second input, using fuzzy text similarity.

Finds records that refer to the same thing even when they are written differently: "Acme Widgets Ltd", "ACME Widgets Limited" and "Acme Widget Ltd.".

**One input connected: de-duplicate.** Every record gets a *Group ID*; records that match each other (directly or through a chain of matches) share it. The first record of each group is marked as the group master.

**Two inputs connected: lookup.** Every record of the first input gets its best match (or best few) from the second input, such as invoices matched to a supplier master list, with the matched fields appended.

Text is normalised first (case, accents, punctuation, "&" vs "and", and optionally company suffixes such as Ltd, Limited, plc, Inc). Choose a similarity measure, a threshold, an optional second field (for example the address) and an optional field that must match exactly (for example the postcode), which also speeds up large inputs.

The second output lists every matching pair with its score, for review and audit.

Pure Python: no packages to install.

## Language
Python

## Inputs
- **Input 1**: records to de-duplicate, or the records to look up.
- **Input 2 (optional)**: the reference list to match against. Connecting it switches the block to lookup mode.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Fields to compare | Match field | `match_field` | Field | The text field to compare, such as a company or customer name. From input 1. |
| Fields to compare | Match field in second input | `reference_field` | Field | Lookup mode only. Leave empty to use the field with the same name as the match field. From input 2. |
| Fields to compare | Second field to compare (optional) | `second_field` | Field | An extra field compared with the same measure, such as an address line. Blended into the score using the weight below. From input 1. |
| Fields to compare | Second field in second input | `second_reference_field` | Field | Lookup mode only. Leave empty to use the field with the same name. From input 2. |
| Fields to compare | Weight of second field | `second_weight` | Decimal number | Share of the score that comes from the second field, from 0 to 1. Default: 0.3. |
| Fields to compare | Must match exactly (optional) | `block_field` | Field | Only records with the same value in this field are compared, such as postcode or country. Improves precision and makes large inputs much faster. From input 1. |
| Fields to compare | Must match exactly, second input | `block_reference_field` | Field | Lookup mode only. Leave empty to use the field with the same name. From input 2. |
| Matching | Similarity measure | `algorithm` | Choice | How the similarity of two values is scored, from 0 (nothing in common) to 1 (identical after clean-up). Choices: Jaro-Winkler, any word order (recommended for names); Jaro-Winkler; Levenshtein edit distance; Word set (ignores extra words); Character trigrams. Default: Jaro-Winkler, any word order (recommended for names). |
| Matching | Match threshold | `threshold` | Decimal number | Pairs scoring at or above this value count as a match. 0.85 to 0.92 suits company names. Default: 0.88. |
| Matching | Matches per record (lookup mode) | `max_matches` | Whole number | How many of the best matches to return for each record of the first input. Default: 1. |
| Text clean-up | Ignore case, accents and punctuation | `normalise` | Tick box | Compare "Café & Co." and "cafe and co" as the same text. Default: ticked. |
| Text clean-up | Ignore company suffixes | `ignore_suffixes` | Tick box | Drop words such as Ltd, Limited, plc, LLP, Inc, Corp, Co, GmbH and The before comparing. Default: ticked. |
| Text clean-up | Other words to ignore | `ignore_words` | Text | Comma-separated words to drop before comparing, such as services, group. |

## Outputs
- **Matched records** (`matched`): De-duplicate: the input with Group ID, Group Size, Is Group Master and Best Match Score. Lookup: the first input with the best match from the second input appended.
- **Match pairs** (`pairs`): Every pair scoring at or above the threshold, with both values and the score.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## Why this rather than the Fuzzy Terms Join block

The community **Fuzzy Terms Join** block (R) joins two inputs by the number of words their text shares. Use this block for character-level similarity (typos, abbreviations, punctuation), to find near-duplicates within one input, or where R isn't available.

As a community block it is less integrated than a core block: it runs as a Python script (slower to start, and it needs Omniscope's Python environment), and it isn't covered by Omniscope's core tests.

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
