# KMeans

Performs KMeans clustering on the first input data provided.
The output consists of the original input with a Cluster field appended. If a second input is available, it will be used as output instead.

## Language
R

## Parameters
### fields.to.use
Adjust to represent the fields you want to cluster on.
### use.all.numeric.fields
If set to true, fields.to.use will be ignored and instead all numeric data fields used
### num.clusters
Predefines the number of clusters

## Dependencies
none

## Source
[kmeans.R](https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/Kmeans/R/kmeans.R)
