from omniscope.api import OmniscopeApi
import pandas

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)
input_data_2 = omniscope_api.read_input_records(input_number=1)

### Input fields

# If you use fields_to_use, make sure to set use_all_numeric_fields = False
fields_to_use = omniscope_api.get_option("fieldsToUse")

field_to_predict = omniscope_api.get_option("fieldToPredict")


### Parameters

use_all_numeric_fields = omniscope_api.get_option("useAllNumericFields")

### Script

import sys
import numpy as np
from sklearn import svm

if input_data is None:
	omniscope_api.abort("No input data")

if use_all_numeric_fields:
    # Get the numeric fields from the input data
    fields_to_use = [x for x in input_data.columns if (input_data[x].dtype == np.float64 or input_data[x].dtype == np.int64 or input_data[x].dtype == "Int64")]

all_fields_to_use = fields_to_use + [field_to_predict]

# Remove invalid rows from the model creating data
input_data = input_data.dropna(subset=all_fields_to_use)

if input_data_2 is None:
	input_data_2 = input_data

# Remove invalid rows from the data to be used for prediction
input_data_2 = input_data_2.dropna(subset=all_fields_to_use)


# Values to predict
y = input_data[field_to_predict]

# Data to predict with
x = input_data[fields_to_use]

if any(type != np.float64 and type != np.int64 and type != "Int64" for type in x.dtypes):
	omniscope_api.abort("Only numeric fields in  \"Fields to use\" are supported")

x = np.array(x, dtype=float)

# Build the model
svm_model = svm.SVC(kernel='rbf', C=1, gamma="auto").fit(x, np.ravel(y))

# New data to predict with
new_x = input_data_2[fields_to_use]

# Make predictions
predictions = pandas.DataFrame(svm_model.predict(new_x), columns=['Prediction'])

# Output the results
output_data = pandas.concat([input_data_2, predictions], axis=1)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()