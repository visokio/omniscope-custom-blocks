# RegEx Parse

Applies a regular expression to a text field: parse capture groups into fields, replace with back-references, tokenise matches into columns or rows, or flag matches.

Regular expressions on a text field, with four modes:

- **Parse**: each capture group `( )` becomes a new field. Named groups such as `(?P<Order>...)` name the fields; otherwise list names in *Output field names*
- **Replace**: replace every match; use `\1` or `$1` to insert captured text (for example, mask card numbers but keep the last four digits)
- **Tokenise**: every match (or its first group) becomes a new **column** (up to a maximum) or a new **row**, such as all SKUs mentioned in a note
- **Match**: a Yes / No field saying whether the text matches the pattern **anywhere**, **at the start** or **completely** (validation)

Case can be ignored; text that is missing stays missing. Python regular expression syntax. Omniscope formulas can already search and replace with regular expressions; this block adds capture groups into fields, tokenising into rows, and a Yes / No match mode.

## Language
Python

## Inputs
- **Input 1**: records with a text field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Pattern | Text field | `field` | Field | The text to apply the regular expression to. From input 1. |
| Pattern | Mode | `mode` | Choice | What to do with each match. Choices: Parse: capture groups to fields; Replace; Tokenise: each match to a column or row; Match: Yes / No. Default: Parse: capture groups to fields. |
| Pattern | Regular expression | `pattern` | Text | For example Order #(?P<Order>[A-Z]-\d+) or [\w.+-]+@[\w-]+\.[\w.]+ |
| Pattern | Ignore case | `ignore_case` | Tick box | Upper and lower case match each other. Default: ticked. |
| Parse and tokenise | Output field names | `output_names` | Text | Comma-separated, in group (or token) order. Optional when the groups are named. |
| Parse and tokenise | Tokenise into | `tokenise_to` | Choice | Choices: Columns; Rows. Default: Columns. |
| Parse and tokenise | Maximum token columns | `max_columns` | Whole number | Default: 5. |
| Parse and tokenise | Keep rows with no tokens (rows mode) | `keep_unmatched` | Tick box | Default: ticked. |
| Replace and match | Replacement text | `replacement` | Text | Use \1 or $1 for the first capture group. |
| Replace and match | Match | `match_type` | Choice | Choices: Anywhere in the text; At the start; The whole text. Default: Anywhere in the text. |
| Replace and match | Output field name (replace / match / rows) | `output_field` | Text | Replace mode: leave empty to overwrite the text field. |

## Outputs
- **Output 1** (`Output Data`): The input with parsed, replaced, tokenised or match fields.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
