"""Model Validation: a confusion matrix and precision, recall and F1 score per class for a classifier's predictions."""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

api = OmniscopeApi()

data = api.read_input_records(input_number=0)
actual_field = api.get_option("ground_truth")
predicted_field = api.get_option("prediction")

if data is None:
    api.abort("Connect records with an actual and a predicted value to the block's input.")
if not actual_field or not predicted_field:
    api.abort("Choose the field with the Actual values and the field with the Predicted values.")
for f in (actual_field, predicted_field):
    if f not in data.columns:
        api.abort(f"{f} is not in the input.")

NO_PREDICTION = "(no prediction)"


def as_label(value):
    """Class labels compared as text, so 1, 1.0 and "1" are the same class."""
    if isinstance(value, (bool, np.bool_)):
        return str(bool(value))
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return str(int(value)) if float(value).is_integer() else f"{float(value):.10g}"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d") if value == value.normalize() else str(value)
    return str(value)


def label_order(labels):
    """Numbers in numeric order, otherwise alphabetical."""
    try:
        return sorted(labels, key=float)
    except ValueError:
        return sorted(labels, key=lambda s: (s.lower(), s))


known = data[data[actual_field].notna()]
no_actual = len(data) - len(known)
actual = known[actual_field].map(as_label)
predicted = known[predicted_field].map(lambda v: NO_PREDICTION if pd.isna(v) else as_label(v))

classes = label_order(set(actual) | (set(predicted) - {NO_PREDICTION}))
columns = classes + ([NO_PREDICTION] if (predicted == NO_PREDICTION).any() else [])

# Confusion matrix: one record per actual class, one field per predicted class
row_name = "Actual class" if "Actual class" not in columns else "Actual class (rows)"
counts = pd.crosstab(actual, predicted).reindex(index=classes, columns=columns, fill_value=0)
matrix = pd.DataFrame({row_name: pd.Series(classes, dtype=object)})
for c in columns:
    matrix[c] = counts[c].to_numpy().astype("int64") if len(classes) else pd.Series([], dtype="int64")

# Scores per class, then the three averages
n_actual = counts.sum(axis=1).astype("int64") if len(classes) else pd.Series([], dtype="int64")
n_predicted = counts[classes].sum(axis=0).astype("int64") if len(classes) else pd.Series([], dtype="int64")
correct = pd.Series([counts.loc[c, c] for c in classes], index=classes, dtype="int64")


def ratio(a, b):
    # a class that is never predicted (or never occurs) scores 0, as in scikit-learn's default
    return np.where(b > 0, a / np.where(b > 0, b, 1), 0.0)


precision = ratio(correct.to_numpy(), n_predicted.to_numpy())
recall = ratio(correct.to_numpy(), n_actual.to_numpy())
f1 = ratio(2 * precision * recall, precision + recall)

scores = pd.DataFrame({
    "Class": pd.Series(classes, dtype=object),
    "Actual records": n_actual.to_numpy(),
    "Predicted records": n_predicted.to_numpy(),
    "Correct": correct.to_numpy(),
    "Precision": precision,
    "Recall": recall,
    "F1 score": f1,
})
total_actual = int(n_actual.sum())
total_correct = int(correct.sum())
total_predicted = int(n_predicted.sum())  # records with a prediction (missing predictions aren't a class)
if len(classes):
    weights = n_actual.to_numpy() / total_actual
    micro_p = total_correct / total_predicted if total_predicted else 0.0
    micro_r = total_correct / total_actual
    micro_f = 2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0
    averages = pd.DataFrame({
        "Class": ["Macro average", "Weighted average", "Micro average"],
        "Actual records": [total_actual] * 3,
        "Predicted records": [total_predicted] * 3,
        "Correct": [total_correct] * 3,
        "Precision": [precision.mean(), (precision * weights).sum(), micro_p],
        "Recall": [recall.mean(), (recall * weights).sum(), micro_r],
        "F1 score": [f1.mean(), (f1 * weights).sum(), micro_f],
    })
    scores = pd.concat([scores, averages], ignore_index=True)
for c in ("Actual records", "Predicted records", "Correct"):
    scores[c] = scores[c].astype("int64")
for c in ("Precision", "Recall", "F1 score"):
    scores[c] = scores[c].astype("float64")
scores["Class"] = scores["Class"].astype(object)

api.write_output(matrix, "confusion")
api.write_output(scores, "precision")

if total_actual:
    message = f"Accuracy {total_correct / total_actual:.1%}: {total_correct} of {total_actual} records predicted correctly."
else:
    message = "No records with an actual value to compare."
if no_actual:
    message += f" {no_actual} records with no actual value were left out."
missing_predictions = int((predicted == NO_PREDICTION).sum())
if missing_predictions:
    message += f" {missing_predictions} records with no prediction were counted as wrong."
api.commit(message)
