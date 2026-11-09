# TSNE

Places the nodes of a network on a 2-D (or 1-D or 3-D) map with t-SNE, so that nodes connected to the same other nodes end up close together and nodes with different connections far apart. Input: one record per connection.

Each input record is one connection between two nodes (people e-mailing each other, customers and the products they buy, pages linking to pages), with an optional weight. The block:

- builds a table with one row and one column per node, holding the total weight of the connections between each pair of nodes. Connections count **in both directions** (a node that only ever receives connections is described by who connects to it), and repeated connections between the same two nodes are **added up**;
- reduces each node's row to **PCA dimensions** dimensions with principal component analysis;
- runs **t-SNE** (t-distributed stochastic neighbour embedding, Barnes-Hut version, from the Rtsne package) on those rows, with the chosen **Perplexity**, for 10,000 iterations;
- outputs each node's coordinates on the map.

Nodes whose connections are alike (the same people, the same products) end up near each other, so groups in the network show up as clusters of points. On a t-SNE map, which nodes sit together is meaningful; the distances between clusters and the sizes of clusters are not.

The map starts from random positions; the block fixes the random seed, so the same input always gives the same map.

## Inputs
- **Input 1**: one record per connection, with a From field, a To field and optionally a numeric Weight field.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Graph | From field | `from` | Field | One end of each connection. |
| Graph | To field | `to` | Field | The other end of each connection. Connections count in both directions. |
| Graph | Weight field | `weight` | Field | Optional: how strong each connection is. Without it every connection counts 1. Must not be negative. |
| Parameters | Number of output dimensions | `outputDimensions` | Integer | 1, 2 or 3 coordinates per node. Default: 2. |
| Parameters | PCA dimensions | `initialDimensions` | Integer | Dimensions kept by the PCA step before t-SNE. Default: 25. |
| Parameters | Perplexity | `perplexity` | Integer | Roughly how many neighbours each node takes into account. Default: 15. Must be at most (number of nodes - 1) / 3. |

## Outputs
- **Map** (`Output Data`): one record per node, in order of first appearance: **Node** (text), **Dimension 1**, **Dimension 2** (and **Dimension 3**) and **Connections** (whole number: the number of connection records the node is part of, at either end).

## Limits

- At least 3 x Perplexity + 1 nodes: 46 with the default perplexity of 15. The block stops with a message giving the largest perplexity the input allows.
- The node table is n x n, so memory and time grow with the square of the number of nodes. In tests: 60 nodes under a second, 1,000 nodes about 15 seconds, 3,000 nodes about 70 seconds.
- Records with a missing From, To or Weight are left out.

## Language and libraries
R, with the **Rtsne** package (BSD 3-Clause; the Barnes-Hut t-SNE C++ code it wraps, by L. van der Maaten, is under a BSD licence with an advertising clause) and **data.table** (MPL-2.0). Install them on the Omniscope server's R if they are missing (`install.packages(c("Rtsne", "data.table"))`).

## Source
[script.R](script.R)

The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` is invented for the demo; `sample-data/make-sample.R` generates it.
