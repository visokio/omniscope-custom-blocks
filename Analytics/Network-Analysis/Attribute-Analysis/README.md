# Attribute Analysis

From a list of connections (each record: a node, the node it connects to, and the first node's category), measures how much each category's connections lead to nodes it shares with each other category, such as which departments work on the same projects.

Each input record is one connection from a **From** node to a **To** node, with the From node's **Category**. Typical inputs:

- people (From) assigned to projects (To), with each person's department (Category): which departments work together?
- customers (From) buying products (To), with each customer's segment: which segments buy the same things?
- authors (From) writing in journals (To), with each author's field.

For each ordered pair of categories A and B, the block gives a **Probability**: the share of A's connections that lead to a To node that B also connects to. In more detail:

- Each category's connections share a total weight of 1 (each of A's connections weighs 1 / number of A's connections), so a large category does not outweigh a small one.
- At each To node, the categories connected to it are mixed in proportion to their weight there.
- For one of A's connections to node T, the other categories at T (not A itself) are rescaled to add up to 1, and the connection is split between them.
- Probability(A, B) adds up, over all A's connections, the connection's weight times B's part at its To node.

So A's probabilities add up to at most 1. What is missing from 1 is the share of A's connections to To nodes that no other category connects to. A category paired with itself is not listed. The measure is not symmetric: Probability(A, B) and Probability(B, A) differ when A and B have different numbers of connections or spread them differently.

Records with a missing From, To or Category are left out. Node names and categories are compared as text, so numeric IDs work. Each connection record counts once; a repeated record counts twice.

## Inputs
- **Input 1**: one record per connection, with a From field, a To field and a Category field (the From node's category).

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Connections | From field | `from` | Field | The node each connection starts from: the one that has the category. |
| Connections | To field | `to` | Field | The node each connection leads to. Categories are compared through the To nodes they share. |
| Category | Category field | `category` | Field | The From node's category. |

## Outputs
- **Category links** (`Output Data`): one record per pair of categories that share at least one To node, sorted by From category and then by Probability, highest first:
  - **From category**, **To category** (text);
  - **Probability** (0 to 1): the share of the From category's connections that lead to To nodes shared with the To category;
  - **Connections** (whole number): the From category's number of connections, to judge how much data a probability rests on.

## Limits

- In tests, 200,000 connections among 20,000 From nodes, 5,000 To nodes and 20 categories took under a second.
- Memory grows with the number of categories that meet at the same To nodes (pairs are built per To node).

## Language and libraries
R, with the **data.table** package (licence: MPL-2.0). Install it on the Omniscope server's R if it is missing (`install.packages("data.table")`).

## Source
[script.R](script.R)

The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` is invented for the demo; `sample-data/make-sample.R` generates it.
