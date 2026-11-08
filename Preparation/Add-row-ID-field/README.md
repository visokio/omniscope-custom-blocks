# Add row ID field

Adds a field numbering the records 1, 2, 3 and so on, in the order they arrive.

Use it to keep the original order of the records before a sort, join or aggregate changes it, or to give records that have no key of their own (survey responses, feedback cards, log lines) one that later blocks and reports can refer to.

- The new field is called **Row ID** unless you name it otherwise; a blank name also gives Row ID.
- Numbering starts at **1**, or at the number you choose (0, 1001, and so on), and goes up by one per record.
- The field is added **last**, or **first** if you tick the option.
- If the input already has a field of that name, its values are **replaced** by the numbers.
- The other fields, their values and types are unchanged. The numbers follow the order of the input, so sort before this block if the order matters.

## Language
Python

## Inputs
- **Input 1**: any records.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| ID field name | `fieldName` | Text | Name of the new field. Left empty, it is Row ID. An existing field of this name is replaced. Default: Row ID. |
| Start at | `startAt` | Integer | The number given to the first record. Default: 1. |
| Put the ID field first | `putFirst` | Yes/no | Make the ID the first field. Unticked (the default), it is added as the last field. |

## Outputs
- **Numbered** (`Output Data`): the input records with the ID field added.

## Size of input

The block streams: Omniscope passes the records through in chunks (10,000 at a time), and the count carries on from one chunk to the next, so the input never has to fit in Python's memory and the numbers run on without gaps or repeats. On an Omniscope server, 300,000 records were numbered 1 to 300,000, each exactly once, in about 8 seconds.

Omniscope's streaming documentation says a stream function may be called more than once on the same chunk; a repeated call would number that chunk on from where the last one stopped. This has not been seen in practice (the server run above had no gaps or repeats); if the numbers matter, check the first and last ID against the record count.

## How it relates to other blocks

- The core **Add row ID** block does the same job without Python: an ID field, a start number, and numbering that can restart within groups (partitions). Prefer it in new workflows; this block remains for projects that already use it and as a small example of a streaming block that keeps a running count.
- `CURRENTROW()` in a Field Organiser formula gives the record number (from 1) without a separate block.

## Dependencies
None beyond pandas, which Omniscope's Python environment provides.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
