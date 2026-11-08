# Standardise

Rescales the chosen number fields to the range 0 to 1 (min-max scaling): each field's lowest value becomes 0, its highest 1, and the rest fall proportionally between.

Prices, percentages, defect rates and lead times are measured in different units and over different ranges, so they can't be compared or added up as they are. Rescaling each to 0 to 1 puts them on one scale: a supplier scorecard can then weight and sum them, a chart can show them side by side, and a distance-based method (clustering, nearest neighbours) doesn't let the field with the largest numbers dominate.

For each chosen field:

new value = (value − lowest) / (highest − lowest)

- **The chosen fields are replaced** by their rescaled values; the other fields pass through unchanged.
- **Missing values stay missing** and are left out when finding the lowest and highest value.
- **A field whose values are all the same becomes 0** in every record that has a value, and the block's message names the field.
- **Number fields only.** A text or date field, no field chosen, or a field no longer in the input stops the block with a message.
- Whole-number fields come out as decimals.

Higher stays higher: in the rescaled field, 1 is the field's highest value. Where lower is better (price, defects, lead time), use `1 - value` in a formula afterwards so that 1 is the best.

## Language and libraries

R. It uses the data.table package (MPL 2.0 licence). data.table is not part of base R: install it on the Omniscope server's R if it is missing (`install.packages("data.table")`).

## Inputs
- **Input 1**: records with one or more number fields.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Input | Fields to standardise | `fields` | Fields | The number fields to rescale, each on its own lowest and highest value. From input 1. |

## Outputs
- **Standardised** (`Output Data`): the input records with each chosen field rescaled to 0 to 1.

## Limits
- **Min-max scaling, not z-scores.** For mean 0 and standard deviation 1, use Omniscope's Normalise block.
- **One extreme value squeezes the rest.** A single very high value becomes 1 and pushes all the others towards 0. Deal with outliers first if the spread matters.
- **The scale comes from the data in this run.** New data with a higher or lower value rescales every record; scores from different runs are not comparable unless the lowest and highest values are the same.

## Size of input

In tests, 500,000 records with two fields took well under a second.

## Source
[script.R](script.R)

The sample data in `sample-data/` is invented for the demo.
