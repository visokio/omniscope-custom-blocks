# Relationship Analysis

Given a dataset in which each record represents an edge between two nodes of a network, the block will project all the nodes onto a (e.g. 2)- dimensional plane in such a way that nodes which share many connections are close together, and nodes that do not share many connections are far apart.

## Language
R

## Input fields
### from.field
Specifies the source of the connection
### to.field
Specifies the target of the connection
### weight.field
Specifies the field containing edge weights. Connections with large weights are considered to be more important and nodes that share many connections of large weight will be projected closer together

## Parameters

### output.dimensions
Number of output dimensions in the data.

### initial.dimensions
An initial step in tsne is a dimensionality reduction via PCA. This variable specifies to how many initial dimensions the network should be reduced.

### perplexity
Specifies more or less how many neighbour points each data point sees. The lower the more local relationships are accentuated.

## Output
### node
Specifies the node
### V1,...
Specifies the nth dimensional projection coordinates. If output.dimensions was set to 2, then the output will contain V1 and V2.


## Dependencies
data.table, Rtsne

## Source
[script.R](https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network%20Analysis/Relationship%20Analysis/R/script.R)
