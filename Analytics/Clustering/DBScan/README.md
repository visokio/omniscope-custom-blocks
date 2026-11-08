# DBScan

Groups records into clusters by density (DBSCAN) on numeric fields and marks isolated records as noise. Outputs the input records with a Cluster field added: 1, 2, 3 and so on for clusters, 0 for noise.

DBSCAN (density-based spatial clustering of applications with noise, Ester, Kriegel, Sander and Xu, 1996) puts records that lie close together on the chosen numeric fields into the same cluster, and records that lie apart from every dense group into none. You do not choose the number of clusters, clusters can have any shape, and the records left over are a ready-made list of outliers.

How the block runs it:

- Each chosen field is **standardised** (mean 0, standard deviation 1) first, so a field measured in thousands does not outweigh one measured in single figures.
- Two records are neighbours when they are within **0.8** standardised units of each other (Euclidean distance), and a cluster needs at least **5** records close together (scikit-learn's `DBSCAN(eps=0.8)`, minimum 5 samples). These two settings are fixed in the script.
- **Cluster** is 1, 2, 3... for the clusters, in the order they are found, and **0 for noise**.
- Records with a missing value in any chosen field are not clustered: they stay in the output with an empty Cluster.
- If the input already has a field called Cluster, it is replaced (and never clustered on, even with "Use all numeric fields").

Because the distances are in standard deviations of the whole field, groups whose centres are closer together than about 0.8 standard deviations merge into one cluster. A few extreme records widen the standard deviation and so pull the other groups closer together.

## Language
Python

## Inputs
- **Input 1**: records with at least one numeric (Integer or Decimal) field.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Use all numeric fields | `useAllNumericFields` | Yes/no | Cluster on every Integer and Decimal field in the input. Untick to choose the fields in "Fields to cluster on". Default: ticked. |
| Fields to cluster on | `fieldsToUse` | Fields | The numeric fields to cluster on. Used when "Use all numeric fields" is unticked. From input 1. |

## Outputs
- **Clustered** (`Output Data`): the input records, in their original order, with a **Cluster** field (whole number): 1, 2, 3... for clusters, 0 for noise, empty where a chosen field is missing.

## Size of input

Memory grows with the number of neighbours each record has, so it depends on how dense the data is as well as on the number of records: records packed into one dense group need far more memory than the same number in well separated groups. The tests run 20,000 records in four well separated groups and check they finish within 60 seconds; larger or denser inputs are not covered by the tests. For larger inputs, cluster a sample first (Random Sample block), or use the core Clustering block.

## Dependencies
scikit-learn, numpy and pandas. The manifest lists `Cython scikit-learn` as dependencies, which Omniscope installs with pip on first run if they are missing; numpy and pandas are part of Omniscope's Python environment. The server needs to be able to install scikit-learn (internet access to the Python package index, or the package installed beforehand).

## Source
[script.py](script.py)

The `Python/` and `R/` folders hold older stand-alone versions of the script (for Omniscope's general Python and R blocks); they are not listed in the block library.

The sample data in `sample-data/` is invented for the demo.
