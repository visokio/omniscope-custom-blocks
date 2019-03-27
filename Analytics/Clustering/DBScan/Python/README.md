# DBScan

Performs DBScan clustering on the first input data provided.
The output consists of the original input with a Cluster field appended. If a second input is available, it will be used as output instead.

## Language
Python

## Parameters
### fields_to_use
Adjust to represent the fields you want to cluster on.
### use_all_numeric_fields
If set to True, fields_to_use will be ignored and instead all numeric data fields used

## Dependencies
sys, numpy, sklearn

## Source
[dbscan.py](https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/DBScan/Python/dbscan.py)
