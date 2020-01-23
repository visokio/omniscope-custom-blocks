# Support Vector Machine Prediction

Predicts classes of new data from old data by drawing a boundary between two classes whereas the margin around the bondary is made as large as possible to avoid touching the points

## Language
Python

## Parameters
### fields_to_use
Adjust to the fields you want to use in the prediction.

### field_to_predict
Specify the field to predict on

### use_all_numeric_fields
If set to True, fields_to_use will be ignored and instead all numeric data fields used

## Dependencies
sys, numpy, sklearn

## Source
[script.py](https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Prediction/SVM/Python/script.py)
