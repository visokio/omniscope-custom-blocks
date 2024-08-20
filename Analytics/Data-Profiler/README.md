# Data Profiler

### This block provides detailed statistics about your dataset. 

It generates information about each field including its data type, basic statistics (such as count, mean, etc.), number of null values, and skewness for numeric fields. 

Additionally, for numeric fields, it calculates a z-score for each data point, identifies potential anomalies (data points that are 3 or more standard deviations away from the mean), and estimates the likelihood of each data point being an anomaly. 

The detailed field statistics are written to the first block output, while the input data enriched with anomaly detection information is written to the second block output.

## Language
Python

## Dependencies
scipy, numpy

## Source
[script.py](https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Data%20Profiler/script.py)
