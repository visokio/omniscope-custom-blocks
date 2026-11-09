# Partition

Numbers records in consecutive groups of a chosen size (1 for the first 1,000 records, 2 for the next 1,000 and so on) in a new Partition field, for processing or sending data in batches.

Many destinations take data a batch at a time: an API that accepts 100 records per request, a mailing service with a daily limit, a file per 50,000 rows, a page of a long listing. The block adds a **Partition** field that says which batch each record belongs to, so the next blocks can filter, group or loop over the batches.

How it numbers the records:

- In the order they arrive: the first *n* records get 1, the next *n* get 2, and so on, where *n* is **Number of records per partition**. The last partition holds whatever is left, so it can be smaller.
- **Partition** is a whole number (Integer), so it sorts and filters as a number (2 before 10).
- An existing field called **Partition** is replaced.
- To batch in a particular order (by date, by region), sort the records first with a Sort block.

The block streams the data (it handles one chunk of records at a time and carries the count on), so it works on inputs of any size without holding them in memory.

## Language and libraries

Python, using pandas (BSD 3-Clause) and numpy (BSD 3-Clause), both part of Omniscope's Python environment. Nothing else to install.

## Inputs
- **Input 1**: any records.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Number of records per partition | `partition_size` | Integer | How many records go in each partition (1 or more). Default: 1000. |

## Outputs
- **Partitioned** (`Output Data`): the input records, in their order, with a **Partition** field (Integer): 1, 2, 3 and so on.

## Size of input

500,000 records took well under a second in tests.

## Source
[script.py](script.py)

The sample data in `sample-data/mailing-list.csv` is invented: made-up contacts with `example.com` addresses.
