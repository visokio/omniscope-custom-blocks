### Input fields

fields_to_use = ["Field 1", "Field 2"]

field_to_predict = "Field 1"]


### Parameters

use_all_numeric_fields = False

### Script

import sys
import numpy as np
from sklearn import svm

if use_all_numeric_fields:
    # Get the numeric fields from the input data
    numeric_cols = [x for x in input_data.columns if (input_data[x].dtype == np.float64 or input_data[x].dtype == np.int64)]
    x = input_data[numeric_cols]
    if 'input_data_2' not in locals():
        new_x = input_data[numeric_cols]
    else:
        new_x = input_data_2[numeric_cols]
else :
    x = input_data[fields_to_use]
    if 'input_data_2' not in locals():
        new_x = input_data[fields_to_use]
    else:
        new_x = input_data_2[fields_to_use]

# Data to predict with
x = np.array(x, dtype=float)

# Values to predict
y = input_data[field_to_predict]

# Build the model
svm_model = svm.SVC(kernel='rbf', C=1).fit(x, np.ravel(y))

# If there's not a second input then use the original data
if 'input_data_2' not in locals():
	input_data_2 = input_data

# Make predictions
predictions = pandas.DataFrame(svm_model.predict(new_x), columns=['Prediction (SVM)'])

# Output the results
output_data = pandas.concat([input_data_2, predictions], axis=1)
