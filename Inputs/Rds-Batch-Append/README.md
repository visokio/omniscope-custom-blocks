# Rds Batch Append

Appends many .rds files saved from R into one output: every .rds file in a folder, or the files listed in an input field. Files with different fields can be lined up first.

A job in R that saves one file per day, month or region (`saveRDS(sales, "sales-2025-03.rds")`) leaves a folder of data frames that belong together. This block reads them all and appends them, so the whole history arrives as one table.

- **Which files**: every file in the **Folder** whose name ends in `.rds` (any case), in name order, including subfolders when **Recursive** is ticked. Or connect an input and choose the **Path field** holding each file's full path (empty paths are skipped; the folder is then ignored).
- **Files with different fields**: with **Scan files first** (the default) every file is read once to collect all the fields, then again to append. The output has every field from every file, in the order first seen; a file without a field gets empty values. A field holding whole numbers in one file and decimals in another becomes decimals.
- **Without scanning**, the first file sets the fields and the three **Schema** options decide what happens when a later file differs: extra fields are left out, missing fields are filled with empty values, and a field of another type is converted. Each can show a warning (listed in the block's message), stop the block, or carry on silently.
- **Types**: factors become text, dates (`Date`) become date-times at midnight UTC, list fields become comma-joined text. Converting text to a number or date gives an empty value where the text isn't one.
- **Add source field** adds a field (default name *Source*) with the path of the file each record came from.

## Language and libraries

R, with the data.table package (Mozilla Public License 2.0). Install it on the Omniscope server's R if it is missing (`install.packages("data.table")`).

## Inputs

- **Input 1** (optional): records with a field holding the full paths of the .rds files to read. When it is connected, the Folder option is ignored.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| Read file names from first input | Path field | `pathField` | Field | The field holding each file's full path, when an input is connected. |
| Read file names from folder | Folder | `folder` | File | The folder to read every .rds file from. |
| Read file names from folder | Recursive | `recursive` | Yes/no | Also read subfolders. Default: yes. |
| Schema | Scan files first | `scanFirst` | Yes/no | Collect the fields of every file first, so the output has them all. Default: yes. |
| Schema | Additional fields | `actionAdditionalFields` | Choice | Without scanning: a file has fields the first did not. Display warning, Stop with an error (default) or Silently ignore; the extra fields are left out. |
| Schema | Missing fields | `actionMissingFields` | Choice | Without scanning: a file lacks fields the first had. Display warning, Stop with an error (default) or Silently ignore; the fields are filled with empty values. |
| Schema | Incorrect field type | `actionIncorrectFieldType` | Choice | A field's type differs: Display warning and convert, Stop with an error (default) or Silently convert. |
| Source | Add source field | `addSourceField` | Yes/no | Add the path of each record's file. Default: no. |
| Source | Source field name | `sourceFieldName` | Text | Name of that field. Default: Source. |

## Outputs

- **Appended** (`Output Data`): the records of every file, one file after another, with the fields lined up, plus the source field when chosen. The block's message says how many files and records were appended, and lists up to five warnings.

## Limits

- Without **Scan files first**, a field the first file holds as whole numbers stays whole numbers: decimals in a later file are cut when converted (2.5 becomes 2). Scan first to avoid it.
- Each file is read whole; files are written to the output one at a time, so memory use follows the largest file. In tests, 100 files of 2,000 records (200,000 in all) appended in under a second.
- Every file must hold a data frame (or matrix); a file holding anything else, or a file that can't be read, stops the block with its name.
- The source field must not have the name of a field in the files.
- R data files can hold code as well as data. Read only files from sources you trust.

## Source

[script.R](script.R)

`sample-data/monthly-sales/` holds three invented monthly extracts (16 records in all; March adds a branch and a Returns field), written by `sample-data/make-sample-data.R`. `sample-data/placeholder.csv` is the block's Appended output for that folder, shown in the demo in place of the block (the demo server can't hold .rds files); a test checks they match.
