# Fuzzy join

Performs a join between the first (left) and second (right) input. The field on which the join is performed must be text containing multiple terms. The result will contain joined records based on how many terms they share, weighted by [inverse document frequency](https://en.wikipedia.org/wiki/Tf%E2%80%93idf)

## Language
R

## Input fields
### input.field.1
The left join field
### input.field.2
The right join field

## Parameters
### join.type
Defines the join type. Possible values are "left", "right", and "left+right". Left joins will find the best matches for all "left" terms, potentially not using all of the "right" terms. Right joins do the opposite. Left+Right joins append individual left and right joins.

## Dependencies
data.table, plyr

## Source
[fuzzy_join.R](https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Fuzzy%20Join/R/fuzzy_join.R)
