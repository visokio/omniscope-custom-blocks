# Inequality Join

Performs a join between the first (left) and second (right) input. The join can be performed using equality/inequality comparators ==, <=, >=, <, > , which means the result will be a constraint cartesian join including
all records that match the inequalities.

## Language
R


## Parameters
### join.on
Specifies the fields from the first and second inputs and the equalities / inequalities that should be applied in the join

## Dependencies
data.table

## Source
[inequality_join.R](https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Inequality%20Join/R/inequality_join.R)
