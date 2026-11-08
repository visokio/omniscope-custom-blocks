# Tile

Assigns records to tiles of a numeric field: quantiles, equal-sum Pareto bands, equal width, standard-deviation bands or manual cut points, optionally within groups.

Puts each record into a numbered band (tile) of a numeric field, by one of five methods:

- **Equal records**: quartiles, deciles, percentiles; each tile has the same number of records
- **Equal sum**: each tile holds the same share of the total, so you see how *few* customers make up the first quarter of revenue
- **Equal width**: tiles of equal value range between minimum and maximum
- **Smart tile**: bands by standard deviations from the mean, labelled *Extremely low* to *Extremely high*
- **Manual**: your own cut points, such as 1000, 5000, 20000

Tiles can be computed **within groups** (deciles per region), numbered from the lowest or the highest values. Each record gets *Tile Number* and *Tile Range* (or *Tile Label* for smart tiles); the second output summarises each tile: records, minimum, maximum, total and shares.

## Language
Python

## Inputs
- **Input 1**: records with a numeric field to tile.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Field and method | Value field | `value_field` | Field | The numeric field to tile. From input 1. |
| Field and method | Method | `method` | Choice | How the tile boundaries are set. Choices: Equal records (quantiles); Equal sum (Pareto bands); Equal width; Smart tile (standard deviations); Manual cut points. Default: Equal records (quantiles). |
| Field and method | Number of tiles | `tiles` | Whole number | 4 for quartiles, 10 for deciles, 100 for percentiles. Not used by smart and manual tiles. Default: 4. |
| Field and method | Manual cut points | `cut_points` | Text | Comma-separated upper bounds, such as 1000, 5000, 20000 (values equal to a cut point go to the next tile up). |
| Options | Within groups (optional) | `group_fields` | Fields | Tile separately within each combination of these fields. From input 1. |
| Options | Tile 1 = highest values | `highest_first` | Tick box | Untick for tile 1 = lowest values. Default: unticked. |
| Options | Name of new fields | `field_prefix` | Text | New fields are '<name> Number' and '<name> Range'. Default: Tile. |

## Outputs
- **Tiled data** (`tiled`): The input with Tile Number and Tile Range (or Tile Label).
- **Tile summary** (`summary`): One row per (group and) tile: records, minimum, maximum, total, share of total, share of records.

## Dependencies
None beyond pandas and numpy, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

## About this block

This block carries the `visokio-agents` tag. It is one of a set of community examples built by Visokio's agents, to extend Omniscope's core blocks with popular, specialist and more unusual use cases, and to show what anyone, people or agents, can build on Omniscope. It is tested by automated tests and was run on a real Omniscope server. It was not reviewed by Omniscope's core team, so it is not on a par with Omniscope's core blocks, which have years of manual, functional and unit tests behind them.

The sample data in `sample-data/` is invented for the demo.
