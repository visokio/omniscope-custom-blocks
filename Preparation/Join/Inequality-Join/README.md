# Inequality Join

Joins the first and second inputs where a number or date field of the first is less than, greater than or equal to a field of the second (<, <=, >, >=, ==), optionally only where another field is equal as well. Every matching pair is output.

An ordinary join pairs records whose keys are equal. Some questions pair records by comparison instead: every campaign a customer was sent **before** each order, every price break an order quantity has **reached**, every reading **above** a threshold. This block joins each record of the first input to every record of the second for which *Left field* *comparator* *Right field* is true.

How it works:

- **Left field** (first input) and **Right field** (second input) must both be numbers or both dates.
- **Comparator**: `Left = Right`, `Left <= Right`, `Left >= Right` (default), `Left < Right` or `Left > Right`.
- **Equal field** (optional, one in each input): a field that must also be equal, such as a customer, product or site. Use one whenever you can: without it, every pair across the whole of both inputs that satisfies the comparison is output.
- **Join type**: **Inner** (default) keeps first-input records with at least one match; **Left** keeps every first-input record, with empty second-input fields where nothing matched.

Things to know:

- **Every match is output.** A record that satisfies the comparison with ten records of the second input appears ten times. To keep only the latest earlier record per row (the rate or price in force at a date), use the As-Of Join block instead.
- **Size**: with `<`, `<=`, `>` or `>=` and no equal field, the output can approach (records in input 1) x (records in input 2).
- **Output order**: the first input's order; a record with several matches is followed by them in the second input's order.
- **Field names**: the first input's fields, then the second input's; a name in both gets `.1` on the second input's copy (`Customer`, `Customer.1`).
- Records with an empty value in the compared field or the equal field match nothing (a Left join keeps them, unmatched).
- The equal fields must be of the same type (both text, both numbers or both dates).

## Language and libraries

R, with the data.table package (Mozilla Public License 2.0) for the join. Install it on the Omniscope server's R if it is missing (`install.packages("data.table")`).

## Inputs
- **Input 1** (left): records with a number or date field to compare.
- **Input 2** (right): records with a number or date field to compare with.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Join | Comparator | `comparator` | Choice | `==`, `<=`, `>=` (default), `<`, `>`: how the left field must compare with the right field. |
| Join | Join type | `joinType` | Choice | Inner (`inner`, default) or Left (`left`). |
| First input | Left field | `left` | Field | The number or date field of the first input. |
| First input | Equal field | `leftKey` | Field | Optional: a field of the first input that must equal the second input's Equal field. |
| Second input | Right field | `right` | Field | The number or date field of the second input. |
| Second input | Equal field | `rightKey` | Field | Optional: the matching field of the second input. Choose both or neither. |

## Outputs
- **Joined** (`Output Data`): every pair of records that satisfies the comparison (and the equal fields), with the first input's fields then the second's; in a Left join, also the unmatched first-input records.

## Size of input

The join itself uses data.table's non-equi join, which does not compare every pair. 10,000 records a side with an equal field of 500 values (about 100,000 output records) took under a second in tests. The output size is the limit: check it with the block's message ("... records out") before adding more data.

## Source
[script.R](script.R)

The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` (orders and marketing campaigns) is invented.
