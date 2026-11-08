# XPT Reader

Reads a SAS transport file (XPORT version 5, `.xpt`): one dataset as records, plus a list of the datasets in the file and their fields.

SAS transport files are how clinical trial data (SDTM and ADaM datasets) is exchanged and submitted to regulators, and how some statistics offices publish data. One file can hold several datasets. This block reads them on the Omniscope server, with nothing to install.

- The **Dataset** output has the records of one dataset: the one named in **Dataset to read**, or the first.
- The **Summary** output lists every dataset in the file: name, label, record count, field count, field names, created and modified.
- The **Fields** output lists every field of every dataset: SAS name, label, type, length and format, and how the block reads it.
- SAS **missing values** (`.`, and the special `.A` to `.Z` and `._`) become empty values.
- Numbers with a SAS **date format** (such as `DATE9.`, `YYMMDD10.`, `E8601DA.`) become dates, and those with a **datetime format** (`DATETIME20.`, `E8601DT.`) become date-times, unless you untick **Read SAS dates as dates**.

## Language and libraries

Python, with pandas (BSD 3-Clause) and numpy (BSD 3-Clause), both part of Omniscope's Python environment. The file format is read by the block's own code, so there is nothing to install.

## Inputs

None. The block reads the file chosen in its options.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| XPT file | `xptFile` | File | The SAS transport file (.xpt) on the Omniscope server. |
| Dataset to read | `datasetName` | Text | The dataset's name in the file, such as `ADSL` (upper or lower case). Empty: the first dataset. |
| Read SAS dates as dates | `convertDates` | Yes/no | Ticked (the default): numbers with a SAS date or datetime format become Date fields. Unticked: they stay as SAS numbers, days or seconds since 1 January 1960. |

## Outputs

- **Summary** (`summary`): Dataset Name, Label, Records, Field count, Fields (the names, comma-separated), Created, Modified.
- **Dataset** (`dataset`): the chosen dataset's records, with its own field names. Text fields have trailing spaces removed; numbers are decimals.
- **Fields** (`variables`): Dataset Name, Position, Field, Label, Type (Number or Text), Length, Format (such as `DATE9.` or `8.1`), Read as (Number, Text or Date).

## Limits

- **XPORT version 5 only**, the format of the XPORT engine and of most submission files. Version 8 files (long names, written by `%LOC2XPT FORMAT=V8`) and CPORT files (`PROC CPORT`) are refused with a message saying so. Native `.sas7bdat` files are a different format.
- Field names are the SAS names (up to 8 characters); labels are in the Fields output.
- Times of day (formats such as `TIME8.`) stay as numbers of seconds.
- The file can have any extension: if the file picker does not offer a `.xpt` file, renaming it (for example to `.xpt.csv`) still works.
- Text is read as Latin-1: transport files do not record their encoding, so text saved as UTF-8 shows accented letters as two characters.
- The whole file is read into memory. In tests, a dataset of 100,000 records with three fields was read in under a second.

## Source

[script.py](script.py)

`sample-data/trial-sample.xpt` is invented (a fictional study with 24 subjects and their blood pressure at three visits) and written by `sample-data/make_sample_xpt.py`. `sample-data/placeholder.csv` is the block's Dataset output for that file, shown in the demo in place of the block (the demo server can't hold .xpt files); a test checks they match.
