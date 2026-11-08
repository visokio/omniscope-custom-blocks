from omniscope.api import OmniscopeApi
import pandas


omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

### Input fields

# Used when "Use all numeric fields" (use_all_numeric_fields) is off
fields_to_use = omniscope_api.get_option("fieldsToUse")

### Parameters

use_all_numeric_fields = omniscope_api.get_option("useAllNumericFields")

### Script

import sys
import numpy as np
from sklearn import cluster, preprocessing

if input_data is None:
    omniscope_api.abort("No input data")


def is_number_field(series):
    return pandas.api.types.is_numeric_dtype(series) and not pandas.api.types.is_bool_dtype(series)


if use_all_numeric_fields:
    # Get the numeric fields from the input data
    # An existing Cluster field (from an earlier clustering) is replaced below, so it is never clustered on
    fields_to_use = [x for x in input_data.columns if x != "Cluster" and is_number_field(input_data[x])]
    if not fields_to_use:
        omniscope_api.abort("The input has no numeric fields to cluster on")
elif not fields_to_use:
    omniscope_api.abort("Choose the fields in \"Fields to cluster on\", or tick \"Use all numeric fields\"")

if any(not is_number_field(input_data[f]) for f in fields_to_use):
    omniscope_api.abort("Only numeric fields can be clustered on: check \"Fields to cluster on\"")

# Records with a missing value in any of the fields are not clustered; they keep an empty Cluster value
complete = input_data[fields_to_use].notna().all(axis=1)

# Data to predict with
x = np.array(input_data.loc[complete, fields_to_use], dtype=float)

cluster_ids = pandas.Series(pandas.NA, index=input_data.index, dtype="Int64")

if len(x) > 0:
    scaler = preprocessing.StandardScaler().fit(x)

    x_t = scaler.transform(x)

    # Build the model
    model = cluster.DBSCAN(eps=0.8).fit(x_t)

    # Cluster 0 is noise (DBSCAN's -1); clusters are numbered from 1.
    # Labels are aligned on the input's own index, so they stay on the record they belong to.
    cluster_ids[complete] = model.labels_ + 1

# Output the results
output_data = input_data.assign(Cluster=cluster_ids)

#write the output records in the first output
omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()
