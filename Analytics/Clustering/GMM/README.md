# Gaussian Mixture Model

Clusters records with a Gaussian mixture model on numeric fields, choosing the number of clusters itself, and gives each record its cluster and the probability that it belongs there. A second input can be assigned to the same clusters.

A Gaussian mixture model treats the data as a mix of several oval clouds of points (multivariate normal distributions). Each cloud has its own centre, size, shape and tilt, so clusters can be long and thin, slanted, or of very different spreads, and they can overlap. Each record gets the cloud it most probably came from, and that probability.

How the block runs it (with the R package mclust):

- mclust fits models with **1 up to "Maximum number of clusters"** clouds and a range of cloud shapes (equal or varying size, shape and orientation), and keeps the one with the best **BIC** (Bayesian information criterion: fit, penalised for the number of parameters). You don't set the number of clusters; you set its upper limit.
- **Cluster** is 1, 2, 3... numbered in the order the clusters first appear in the input: the first record's cluster is 1.
- **Cluster probability** is the model's probability (0 to 1) that the record belongs to its cluster. Values well below 1 mark records between two clusters.
- **Second input** (optional): its records are assigned to the clusters fitted on the first input, with the same numbering. It must have fields with the same names as the chosen fields; other fields are kept as they are.
- Records with a missing value in any chosen field are not clustered: they stay in the output, in their place, with both fields empty.
- If an input already has fields called Cluster or Cluster probability, they are replaced (and never clustered on).
- The fields are used as they are, not standardised: the model's clouds stretch to fit each field's spread.
- The same input gives the same result on every run. (Above 2,000 records mclust starts from a random sample of 2,000; the block fixes the seed.)

## Inputs
- **Input 1**: records with at least one numeric (Integer or Decimal) field. The model is fitted on these.
- **Input 2** (optional): records to assign to the clusters, with the same numeric fields.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Use all numeric fields | `useAllNumericFields` | Yes/no | Cluster on every Integer and Decimal field in the first input. Untick to choose the fields in "Fields to cluster on". Default: ticked. |
| Fields to cluster on | `fieldsToUse` | Fields | The numeric fields to cluster on. Used when "Use all numeric fields" is unticked. From input 1. |
| Maximum number of clusters | `maxClusters` | Integer | Models with 1 up to this many clusters are compared. Default: 9 (mclust's own default). 1 to 30. |

## Outputs
- **Clustered** (`Output Data`): the first input, in its original order, with **Cluster** (whole number) and **Cluster probability** (0 to 1).
- **Assigned** (`Output Data 2`): the second input with **Cluster** and **Cluster probability**. Written only when a second input is connected.

## Limits

- At least 2 records with values in the chosen fields; the block stops with a message if no model can be fitted (for example when every value is the same).
- Time grows with the number of records, fields and the maximum number of clusters. In tests, 150 records took well under a second, and 10,000 records on three fields with the default maximum of 9 took about 13 seconds.

## Language and libraries
R, with the **mclust** package (licence: GPL 2 or later). mclust is not part of base R: install it on the Omniscope server's R if it is missing (`install.packages("mclust")`).

## Source
[script.R](script.R)

The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` is invented for the demo; `sample-data/make-sample.R` generates it.
