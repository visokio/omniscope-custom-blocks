# UK Postcode Tools

Validates, standardises and extracts UK postcodes and splits them into area, district and sector with area name and country, offline.

Cleans and enriches **UK postcodes**, offline:

- **Validates** each value against the official UK postcode format and the list of postcode areas, with the reason when it fails (wrong length, invalid outward or inward code, unknown area)
- **Standardises** to upper case with a single space (`ls15hd` becomes `LS1 5HD`), and fixes the common slip of the letter O for zero in the inward code
- **Extracts** the postcode from a free-text address field when asked
- **Splits** into **area** (`LS`), **district** (`LS1`), **sector** (`LS1 5`) and adds the **area name** (Leeds) and **country** (England, Scotland, Wales, Northern Ireland, Channel Islands, Isle of Man; cross-border areas are labelled as such)

The second output counts records per postcode area and per problem, a quick data-quality and geography summary.

Format and area checks only: a well-formed postcode that does not exist cannot be detected without a lookup service (such as the ONS Postcode Directory, which can be joined afterwards on the formatted postcode).

## Language
Python

## Inputs
- **Input 1**: records with a postcode field or a free-text address field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Postcodes | Postcode or address field | `postcode_field` | Field | From input 1. |
| Postcodes | Find the postcode inside the text | `extract_from_text` | Tick box | Tick when the field is a full address rather than just a postcode. Default: unticked. |
| Postcodes | Replace the field with the formatted postcode | `replace_field` | Tick box | Otherwise a new field is added. Ignored when extracting from text. Default: unticked. |
| Postcodes | Prefix for new fields | `prefix` | Text | New fields are '<prefix> Valid', '<prefix> Area' and so on. Default: Postcode. |

## Outputs
- **Postcodes** (`postcodes`): The input with formatted postcode, validity, problem, area, district, sector, area name and country.
- **Area summary** (`areas`): Records per country and postcode area, plus counts per problem for invalid postcodes.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
