# Field Renamer

Renames the fields of a data set from a list of rules (current name, new name) held in another data set, and lists the rules that matched nothing and the fields left unchanged.

Systems export fields under short or technical names (`cust_nm`, `last_ord_dt`). When there are many of them, or the list changes, keeping the renames as data (a spreadsheet, a database table, a Text Input block) is easier than setting each one up by hand. This block reads the rules from its first input and applies them to the data in its second input.

- One rule per field to rename: a field holding the **current name** and a field holding the **new name**.
- Names are matched **exactly**, including capitals. Spaces at either end of a name in the rules are ignored.
- Fields with no rule **keep their names**; values and types are never changed.
- Rules naming a field the data doesn't have are skipped and listed on the **Unused rules** output; the data's fields that no rule renamed are listed on **Unchanged**. Together they show whether the rules still fit the data.
- Two names can be swapped (A to B and B to A in the same rules).
- A rule with no current name is skipped. The block stops with a message if a rule has no new name, if a current name appears twice, or if renaming would give two fields the same name.

## Language
R

## Inputs
- **Input 1** (rules): one record per field to rename, with a field for the current name and a field for the new name. Any field types; names are read as text.
- **Input 2** (data): the records whose fields are renamed.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Current field names | `currentNames` | Field | The field in the rules (first input) that holds each field's current name. |
| New field names | `newNames` | Field | The field in the rules (first input) that holds the name to give it. |

## Outputs
- **Renamed** (`Output Data`): the second input with its fields renamed; values unchanged.
- **Unused rules** (`Unused`): the rules whose current name is not a field of the data, with the fields `Current Name` and `New Name`.
- **Unchanged** (`Unchanged`): one record per field of the data that no rule renamed, in the field `Field`.

## Size of input

Only the field names change; the values are not copied or converted by the script. In tests, 20,000 records with 2,000 fields, all renamed, took well under a second.

## Dependencies
R with the `data.table` package (MPL-2.0 licence). Install it on the Omniscope server's R (`install.packages("data.table")`) if it is missing.

## Source
[script.R](script.R)

The sample data in `sample-data/` is invented for the demo.
