from omniscope.api import OmniscopeApi
import pandas


omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

### Input fields

# If you use fields_to_use, make sure to set use_all_numeric_fields = False
fields_to_use = omniscope_api.get_option("fieldsToUse")

### Parameters

use_all_numeric_fields = omniscope_api.get_option("useAllNumericFields")

### Script

import sys
import numpy as np
from sklearn import cluster, preprocessing

if input_data is None:
	omniscope_api.abort("No input data")

if use_all_numeric_fields:
    # Get the numeric fields from the input data
    fields_to_use = [x for x in input_data.columns if (input_data[x].dtype == np.float64 or input_data[x].dtype == np.int64 or input_data[x].dtype == "Int64")]

# Remove invalid rows from the model creating data
input_data = input_data.dropna(subset=fields_to_use)

# Data to predict with
x = input_data[fields_to_use]

if any(type != np.float64 and type != np.int64 and type != "Int64" for type in x.dtypes):
	omniscope_api.abort("Only numeric fields in  \"Fields to use\" are supported")

x = np.array(x, dtype=float)

scaler = preprocessing.StandardScaler().fit(x)

x_t = scaler.transform(x)

# Build the model
model = cluster.DBSCAN(eps=0.8).fit(x_t)

# Get labels
labels = pandas.DataFrame(model.labels_+1, columns=["Cluster"])

# Output the results
output_data = pandas.concat([input_data, labels], axis=1)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()
