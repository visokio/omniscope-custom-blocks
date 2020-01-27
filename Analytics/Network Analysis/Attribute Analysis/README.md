# Attribute Analysis

Given a dataset in which each record represents an edge between two nodes of a network, and each node has an associated categorical attribute, the block analyses connections between attributes, based on connections between associated nodes. The result of the analysis is a list of records in which each record specifies a connection from one attribute to another. The connection contains a probability field, which gives an answer to the question that if a node has the specified categorical attribute, how probable it is that it has a connection to another node with the linked categorical attribute.

## Language
R

## Input fields
### from.field
Specifies the source of the connection
### to.field
Specifies the target of the connection
### category.field
Specifies the field containing the categorical attribute

## Output
The output consists of three fields:
### from
Specifies the source of the categorical attribute
### to
Specifies the target of the categorical attribute
### probability
Specifies the probability that if a node has the categorical attribute specified by "from", it will have a connection to a node with the categorical atribute specified by "to".


## Dependencies
data.table

## Source
[script.R](https://github.com/visokio/omniscope-custom-blocks/blob/master/Analytics/Network%20Analysis/Attribute%20Analysis/R/script.R)
