# K-Nearest-Neighbours

Predicts a category for each record from the k most similar records whose category is known (k-nearest neighbours), on numeric fields standardised first, with the share of neighbours that agree.

k-nearest neighbours needs no model to be fitted: to classify a record, it finds the **k** records with a known category that are closest to it on the chosen numeric fields, and predicts the category most of them have. It suits categories that form groups in the data, whatever their shape.

How the block runs it (R's `class` package):

- **Training records** are the first input's records that have a value in the field to predict and in every field to predict from.
- **Two inputs**: every record of the second input is predicted from the training records.
- **One input**: every record of the first input is predicted. Records with a known category are predicted from the *other* known records (leave-one-out), so the prediction never sees the record's own answer and comparing the two fields shows how often the block is right. Records with no category are predicted from all known records.
- Each field is **standardised** first (mean 0, standard deviation 1, from the training records), so a field measured in thousands does not outweigh one measured in single figures. Untick **Standardise fields** to use the raw values.
- Distances are Euclidean. When votes tie, or several records are equally distant at the k-th place, R breaks the tie at random; the block fixes the seed, so the same input always gives the same predictions.
- **Predicted (*field*)** holds the predicted category; **Vote share** is the share of the k neighbours (and of any records tied with the k-th) that have it, 0 to 1.
- Records with a missing value in a field to predict from keep their place, with both fields empty. Existing fields with these names are replaced.

## Inputs
- **Input 1**: records with a Text field holding the category, where known, and numeric (Integer or Decimal) fields to predict from.
- **Input 2** (optional): records to classify, with numeric fields of the same names.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Field to predict | `fieldToPredict` | Field | The Text field holding the category, in the first input. Required. |
| Use all numeric fields | `useAllNumericFields` | Yes/no | Predict from every Integer and Decimal field in the first input. Default: ticked. |
| Fields to predict from | `fieldsToUse` | Fields | The numeric fields that measure similarity, when "Use all numeric fields" is unticked. |
| Number of neighbours | `numberOfNeighbours` | Integer | The k: how many of the most similar known records vote. Default: 5. |
| Standardise fields | `standardise` | Yes/no | Rescale each field to mean 0 and standard deviation 1 first. Default: ticked. |

## Outputs
- **Predicted** (`Output Data`): the second input (or, with one input, the first), in its original order, with **Predicted (*field*)** (text) and **Vote share** (decimal, 0 to 1).

## Limits

- Number of neighbours must be less than the number of training records.
- Every prediction compares the record with every training record. In tests, 20,000 training records and 20,000 records to classify on two fields took about 1 second.

## Language and libraries
R, with the **class** package (licence: GPL-2 or GPL-3), which comes with R as one of its recommended packages; install it with `install.packages("class")` if the server's R lacks it.

## Source
[script.R](script.R)

The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` is invented for the demo; `sample-data/make-sample.R` generates it.
