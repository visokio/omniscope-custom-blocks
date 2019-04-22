### Input fields

fields_to_use = ["Field 1", "Field 2"]

### Parameters

use_all_numeric_fields = True

### Script

import sys
import numpy as np
from sklearn import cluster, preprocessing

if use_all_numeric_fields:
    # Get the numeric fields from the input data
    numeric_cols = [x for x in input_data.columns if (input_data[x].dtype == np.float64 or input_data[x].dtype == np.int64)]
    x = input_data[numeric_cols]
else :
    x = input_data[fields_to_use]

# Data to predict with
x = np.array(x, dtype=float)

scaler = preprocessing.StandardScaler().fit(x)

x_t = scaler.transform(x)

# Build the model
model = cluster.DBSCAN(eps=0.8).fit(x_t)

# Get labels
labels = pandas.DataFrame(model.labels_+1, columns=["Cluster (DBSCAN)"])

# Output the results
output_data = pandas.concat([input_data, labels], axis=1)
