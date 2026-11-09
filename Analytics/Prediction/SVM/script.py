"""Support Vector Machine: learns a category from the records on the first input and predicts it for the records
on the second input (or, with no second input, for the first input's own records)."""
import numpy as np
import pandas as pd
from omniscope.api import OmniscopeApi

api = OmniscopeApi()

training = api.read_input_records(input_number=0)
to_predict = api.read_input_records(input_number=1)

fields_to_use = api.get_option("fieldsToUse")
field_to_predict = api.get_option("fieldToPredict")
use_all_numeric_fields = api.get_option("useAllNumericFields")

if training is None:
    api.abort("Connect the records with a known category (the training data) to the first input.")
if not field_to_predict:
    api.abort("Choose the Field to predict.")
if field_to_predict not in training.columns:
    api.abort(f"The Field to predict, {field_to_predict}, is not in the first input.")


def is_number(series):
    return pd.api.types.is_numeric_dtype(series.dtype) and not pd.api.types.is_bool_dtype(series.dtype)


if use_all_numeric_fields:
    # every numeric field except the one being predicted (using it would predict the answer from itself)
    fields = [f for f in training.columns if f != field_to_predict and is_number(training[f])]
    if not fields:
        api.abort("The first input has no numeric fields to predict from, other than the Field to predict.")
else:
    if not fields_to_use:
        api.abort("Choose the Fields to predict from, or tick \"Use all numeric fields\".")
    fields = [f for f in fields_to_use if f != field_to_predict]
    if not fields:
        api.abort("The Fields to predict from must include a field other than the Field to predict.")
    absent = [f for f in fields if f not in training.columns]
    if absent:
        api.abort("Not in the first input: " + ", ".join(absent))
    text = [f for f in fields if not is_number(training[f])]
    if text:
        api.abort("Only numeric fields can be used to predict from. Not numeric: " + ", ".join(text))

scoring_own_records = to_predict is None
if scoring_own_records:
    to_predict = training
else:
    absent = [f for f in fields if f not in to_predict.columns]
    if absent:
        api.abort("The second input needs the same fields to predict from. Not in the second input: "
                  + ", ".join(absent))
    text = [f for f in fields if not is_number(to_predict[f])]
    if text:
        api.abort("These fields are not numeric in the second input: " + ", ".join(text))

# Train on the records that have every value (the fields and the known category)
complete_training = training.dropna(subset=fields + [field_to_predict])
if len(complete_training) == 0:
    api.abort("No record on the first input has the Field to predict and all the fields to predict from.")
target = complete_training[field_to_predict]
if target.nunique() < 2:
    api.abort(f"The Field to predict needs at least two different values to learn from; "
              f"the training records only have {target.iloc[0]!r}.")

from sklearn import svm  # noqa: E402  (imported here so the checks above report before a slow import)
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

x = complete_training[fields].astype("float64").to_numpy()
if pd.api.types.is_bool_dtype(target.dtype):
    y = target.to_numpy(dtype=bool)
elif is_number(target):
    y = target.to_numpy(dtype="float64")
else:
    y = target.astype(str).to_numpy(dtype=object)
# Each field is standardised first, so a field measured in thousands doesn't drown out one measured in units
model = make_pipeline(StandardScaler(), svm.SVC(kernel="rbf", C=1, gamma="auto")).fit(x, y)

output = to_predict.copy()
if "Prediction" in output.columns:
    output = output.drop(columns="Prediction")
can_predict = output[fields].notna().all(axis=1)
# The Prediction field has the Field to predict's type, with room for empty values
target_dtype = training[field_to_predict].dtype
if pd.api.types.is_bool_dtype(target_dtype):
    target_dtype = "boolean"
elif pd.api.types.is_integer_dtype(target_dtype):
    target_dtype = "Int64"
prediction = pd.Series(pd.array([None] * len(output), dtype=target_dtype), index=output.index)
if can_predict.any():
    predicted = model.predict(output.loc[can_predict, fields].astype("float64").to_numpy())
    prediction.loc[can_predict] = pd.array(predicted).astype(prediction.dtype)
output["Prediction"] = prediction

api.write_output(output, "Output Data")
skipped = int((~can_predict).sum())
api.commit(f"Trained on {len(complete_training)} records ({len(fields)} fields); predicted "
           f"{int(can_predict.sum())} records" + (f", {skipped} left empty (missing values)." if skipped else "."))
