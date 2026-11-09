# KMeans

Groups records into a chosen number of clusters with k-means on numeric fields, standardised first. Outputs the input records with a Cluster field added.

k-means puts each record in the cluster whose centre (the average of the cluster's records on the chosen fields) is nearest, and moves the centres until no record changes cluster. You choose the number of clusters; every record with values in the chosen fields goes into one of them.

How the block runs it:

- Each chosen field is **standardised** (mean 0, standard deviation 1) first, so a field measured in thousands does not outweigh one measured in single figures. Untick **Standardise fields** when the fields share a unit and scale (latitude and longitude, or several percentages).
- Distances are Euclidean. The block runs R's `kmeans()` (Hartigan-Wong) from **10 random starts** and keeps the best, with a **fixed random seed**, so the same input always gives the same clusters.
- **Cluster** is 1, 2, 3... numbered in the order the clusters first appear in the input: the first record's cluster is 1.
- Records with a missing value in any chosen field are not clustered: they stay in the output, in their place, with an empty Cluster.
- If the input already has a field called Cluster, it is replaced (and never clustered on).

k-means works best on compact, roughly round groups of similar size. It always makes the number of clusters you ask for, whether or not the data has that many groups, and a few extreme records can take a cluster of their own. Try two or three values of **Number of clusters** and compare the cluster averages (Aggregate block on Cluster).

## Inputs
- **Input 1**: records with at least one numeric (Integer or Decimal) field.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Use all numeric fields | `useAllNumericFields` | Yes/no | Cluster on every Integer and Decimal field in the input. Untick to choose the fields in "Fields to cluster on". Default: ticked. |
| Fields to cluster on | `fieldsToUse` | Fields | The numeric fields to cluster on. Used when "Use all numeric fields" is unticked. From input 1. |
| Number of clusters | `numClusters` | Integer | How many clusters to make (the k in k-means). Default: 4. |
| Standardise fields | `standardise` | Yes/no | Rescale each chosen field to mean 0 and standard deviation 1 before clustering. Default: ticked. |

## Outputs
- **Clustered** (`Output Data`): the input records, in their original order, with a **Cluster** field (whole number): 1, 2, 3..., empty where a chosen field is missing.

## Limits

- Number of clusters must not be more than the number of distinct combinations of values in the chosen fields; the block stops with a message if it is.
- In tests, 50,000 records on three fields into five clusters took about 1 second.

## Language and libraries
R. It uses only `kmeans()` from the `stats` package that comes with every R installation (GPL-2 or GPL-3, like R itself). Nothing to install.

## Source
[script.R](script.R)

The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` is invented for the demo; `sample-data/make-sample.R` generates it.
