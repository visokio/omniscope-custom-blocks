# Fuzzy Terms Join

Joins two inputs on text fields that are written differently but share words, such as company names or product descriptions. Each record is paired with the record on the other side that shares the most distinctive words.

"Harbourside Packaging", "HARBOURSIDE PACKAGING LTD" and "Harbourside Packaging Limited" share the words that matter, in any order and any case. An exact join finds none of these pairs; this block pairs each with the record it shares the most distinctive words with.

How a match is scored:

- **Words** are runs of letters, compared in lower case. Digits, punctuation and spaces separate words and are dropped, and one-letter words are ignored. So "Precision Eng. Tamworth" has the words *precision*, *eng* and *tamworth*, and "O'Neill" has only *neill*.
- Each shared word scores its **inverse document frequency** (IDF) in the input being matched: log(number of words in that input / number of times this word occurs in it). A word that appears in many records, such as "ltd" or "services", scores little; a distinctive name scores a lot.
- A record's score against a candidate is the sum over the words they share (a word repeated in either text counts each time it is paired). The candidate with the highest score is the match; when two candidates tie, the one later in the input wins.

Join types:

- **Left**: every first-input record that shares at least one word with the second input gets its best match from the second input. Weights come from the first input.
- **Right**: the same the other way round. Weights come from the second input.
- **Left + Right**: both results, one after the other. A pair found from both sides appears twice.

Things to know:

- **Records with no word in common are left out**, so a Left join is not a left outer join: compare the record count with the input's to find unmatched records.
- **There is no minimum score.** A record whose only shared word is a common one ("ltd") still gets a match. Check the matches, for example by sorting the output on the two text fields side by side.
- **Each record gets one match**, so several records on one side can match the same record on the other side.
- **Field names**: when both inputs have a field with the same name, the output has it twice, with `.x` and `.y` added: `.x` is the first input in Left and Left + Right joins, and the second input in a Right join. Spaces and other characters that are not allowed in R names become dots (`Supplier Name` becomes `Supplier.Name`).
- The inputs must not contain fields called `.index`, `.index.x` or `.index.y`; the block uses those names internally.

## Language
R

## Inputs
- **Input 1** (left): records with a text field to match on.
- **Input 2** (right): records with a text field to match on.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Join | Join type | `joinType` | Choice | Left, Right or Left + Right (`left`, `right`, `left+right`): which side's records each get a best match. Default: Left. |
| First input | Left field | `left` | Field | The text field to match on in the first (left) input. |
| Second input | Right field | `right` | Field | The text field to match on in the second (right) input. |

## Outputs
- **Joined** (`Output Data`): one record per match, with the fields of both inputs (first input's fields first in a Left join, second input's first in a Right join).

## Size of input

The matching compares every pair of records that share a word, so words that occur in many records on both sides (such as "Ltd" in half of all company names) make it slow. In tests, 10,000 records a side with no such word joined in under a second; 10,000 a side with "Ltd" in half the names took 17 seconds and about 3.3 GB, and 20,000 a side took 87 seconds and about 13 GB.

## Dependencies
R with the `data.table` package. Install it on the Omniscope server's R (`install.packages("data.table")`) if it is missing. Earlier versions also loaded `plyr`; it is no longer needed.

## Source
[script.R](script.R)

The `R/` folder holds an older stand-alone version of the script (for Omniscope's general R block); it is not listed in the block library.

The sample data in `sample-data/` is invented for the demo.
