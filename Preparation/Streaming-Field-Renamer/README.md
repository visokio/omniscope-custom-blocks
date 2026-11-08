# Streaming Field Renamer

Renames the fields of the input from rename rules (current name, new name) written in the block or kept in a CSV file, working through the data in chunks so large inputs never have to fit in memory.

Write the renames in the block, or keep a system's renames in one CSV file and point every project that reads its exports at it. The block streams: Omniscope passes the data through in chunks, so the number of records doesn't limit it.

A streaming block has exactly one input, so the rules can't come from a second, rules-table input; they are an option instead.

- **Rename rules** (written in the block): one rule per line, or rules separated by semicolons, each `Current Name = New Name`, for example `acct_no = Account Number; txn_dt = Transaction Date`. When filled in, it takes precedence over the file. A name containing `=` or `;` needs the file.
- **Rename rules CSV file**: used when Rename rules is empty. It has the columns **Current Name** and **New Name**, one rule per field to rename. Capitals and spaces in the two column headings are ignored, and so is a byte order mark at the start of the file.
- Field names are matched **exactly**, including capitals. Spaces at either end of a name in the rules are ignored. Names in the file are always read as text, so a field called `2024` or `NA` can be renamed.
- Fields with no rule **keep their names**; rules naming a field the input doesn't have are ignored. Values and types are never changed.
- Two names can be swapped (A to B and B to A in the same file).
- Rules with an empty current name (blank lines) are skipped. The block stops with a message if a rule has no new name, if a current name appears twice, or if renaming would give two fields the same name.

Example rules file:

```
Current Name,New Name
acct_no,Account Number
txn_dt,Transaction Date
```

To keep the rules in a data set rather than a file, or to list the rules that matched nothing, use the **Field Renamer** block.

## Language and libraries

Python. It uses pandas (BSD 3-Clause), part of Omniscope's Python environment. Nothing else to install.

## Inputs
- **Input 1**: the records whose fields are renamed.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Rename rules | `rulesText` | Text | Rules written in the block, one per line or separated by semicolons: Current Name = New Name. Takes precedence over the file. |
| Rename rules CSV file | `rules` | File | A CSV file with the columns Current Name and New Name, one rule per field to rename. UTF-8 text; the first line holds the column headings. Used when Rename rules is empty. |

## Outputs
- **Renamed** (`Output Data`): the input with its fields renamed; values unchanged.

## Size of input

The data passes through in chunks and only the field names change, so the block itself holds one chunk at a time. In tests, 200,000 records with 500 fields, all renamed, took about a second.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
