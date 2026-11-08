# Model Validation

Checks a classifier's predictions against the actual values: a confusion matrix, and precision, recall and F1 score for each class with macro, weighted and micro averages.

Use it on records where you know both the true category and the one a model predicted: the Prediction or Support Vector Machine block run on records held back from training, a scoring rule, or predictions made outside Omniscope. It answers "how often is the model right?" and, more usefully, "which categories does it get wrong, and what does it mistake them for?".

- Values are compared **as text**, so 1, 1.0 and "1" are the same class. Classes are sorted in numeric order when they are all numbers, otherwise alphabetically.
- Every class found in **either** field is in the results, including a class the model never predicts.
- Records with **no actual value** are left out (there is nothing to compare). Records with **no prediction** are counted as wrong: they appear in a **(no prediction)** field of the matrix and lower the recall of their actual class.

## Language
Python

## Inputs
- **Input 1**: records with an actual and a predicted category.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Actual values | `ground_truth` | Field | The field with the true category of each record. |
| Predicted values | `prediction` | Field | The field with the category the model predicted. |

## Outputs
- **Matrix** (`confusion`): the confusion matrix. One record per actual class (field **Actual class**) and one field per predicted class, plus **(no prediction)** when some records have none; each cell is the number of records with that actual and predicted class. Correct predictions are on the diagonal. The fields depend on the classes in the data.
- **Scores** (`precision`): one record per class with **Actual records** (how many records really are that class), **Predicted records**, **Correct**, **Precision** (correct ÷ predicted), **Recall** (correct ÷ actual) and **F1 score** (their harmonic mean), followed by three averages:
  - **Macro average**: the plain average over the classes, so a rare class counts as much as a common one;
  - **Weighted average**: weighted by each class's actual records;
  - **Micro average**: from the totals over all records. Its recall is the **accuracy** (correct ÷ all records compared), which the block also reports in its finishing message.

A class that is never predicted has a precision of 0, and a class that never occurs a recall of 0, as in scikit-learn's default; both count in the macro and weighted averages.

## Limits
- For categories only. For predicted amounts (forecasts, regression), use the community **Forecast Accuracy** block.
- One matrix for all records: for a matrix per group (per region, per month), filter first or run the block once per group.
- In tests, 200,000 records with 20 classes took under a second.

## Dependencies
None beyond pandas and numpy (BSD licence), which Omniscope's Python environment provides. The scores are computed directly; the tests check them against scikit-learn's.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo; `generate.py` there recreates it.
