# Gaussian Mixture Model

Performs GMM clustering on the first input data provided.
The output consists of the original input with a Cluster field appended. If a second input is available, it will be used as output instead.

## Language
R

## Parameters
### fields.to.use
Adjust to represent the fields you want to cluster on.
### use.all.numeric.fields
If set to true, fields.to.use will be ignored and instead all numeric data fields used

## Dependencies
mclust

## Source
[gmm.R](https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Clustering/GMM/R/gmm.R)
