# Support Vector Machine

Predicts a category (such as Normal, Worn or Faulty) for new records from numeric fields, using a support vector machine trained on records whose category is known.

A support vector machine learns the boundaries between categories from examples. Give it records where the answer is known (pumps an engineer has inspected, customers who did or didn't renew) and records where it isn't yet, and it predicts the answer for the second set from the same numeric measurements.

How the block runs it:

- The **first input** is the training data: records with the **Field to predict** filled in. Records with a missing value in that field or in any field used to predict are left out of the training.
- The **second input** (optional) holds the records to predict. With nothing connected there, the block predicts the first input's own records, which shows how well the model fits the examples it learnt from (always better than it will do on new records).
- With **Use all numeric fields** ticked, every Integer and Decimal field except the Field to predict is used; otherwise the **Fields to predict from** you choose.
- Each field is **standardised** (mean 0, standard deviation 1, from the training records) first, so a field measured in thousands, such as runtime hours, counts as much as one measured in units.
- The model is scikit-learn's `SVC` with a radial basis function kernel, `C=1` and `gamma="auto"` (1 ÷ number of fields). These settings are fixed in the script.
- The output is the records to predict with a **Prediction** field of the same type as the Field to predict. Records with a missing value in a field used to predict keep their place, with an empty Prediction.

## Language
Python

## Inputs
- **Input 1**: training records, with the Field to predict and numeric fields to predict from.
- **Input 2** (optional): the records to predict, with the same numeric fields. They don't need the Field to predict.

## Options

| Option | Name in script | Type | Default | Description |
|---|---|---|---|---|
| Field to predict | `fieldToPredict` | Field | | The category to learn from the first input and predict. Text or whole numbers. |
| Use all numeric fields | `useAllNumericFields` | Yes/no | ticked | Predict from every Integer and Decimal field except the Field to predict. |
| Fields to predict from | `fieldsToUse` | Fields | | The numeric fields the prediction is based on, when "Use all numeric fields" is unticked. From input 1. |

## Outputs
- **Predicted** (`Output Data`): the records to predict (input 2, or input 1 if input 2 is not connected), in their original order, with a **Prediction** field. An existing field called Prediction is replaced.

## Limits
- Only numeric fields are used to predict from. Turn categories such as Site into numbers first if they matter (for example one 0/1 field per value with a Formula block).
- The block predicts categories, not amounts: a Decimal Field to predict is treated as a list of categories.
- There is no probability or confidence for each prediction. Check accuracy on records with a known answer that were not used for training: split the known records (Split data block), train on one part, predict the other, and compare with the **Model Validation** block.
- Training time grows faster than the number of training records. In tests with three overlapping categories and three fields, predicting 100,000 records took 7 seconds with 5,000 training records, 35 seconds with 20,000 and 2.5 minutes with 50,000. For more training records, train on a sample (Random sample block).

## Dependencies
scikit-learn (BSD licence), listed in the block's dependencies, so Omniscope installs it with pip on first run if it is missing; the server needs access to the Python package index for that, or scikit-learn installed beforehand. pandas and numpy (BSD licence) come with Omniscope's Python environment.

## Source
[script.py](script.py)

The `Python/` folder holds an older stand-alone version of the script (for Omniscope's general Python block); it is not listed in the block library.

The sample data in `sample-data/` is invented for the demo; `generate.py` there recreates it. `pump-readings-inspected.csv` holds what an engineer later found for each of the 30 pumps, to check the predictions against.
