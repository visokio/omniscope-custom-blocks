# R Data Reader

Reads a table from an R data file (.rds, .rda or .RData): a data frame, matrix or vector saved from R. A second output lists the objects in the file.

Analysts working in R save their results with `saveRDS()` (one object per .rds file) or `save()` (several objects in one .rda or .RData file). This block reads those files directly, so the data can go into an Omniscope workflow without first being exported to CSV.

- **A .rds file**: its one object is loaded.
- **An .rda or .RData file**: leave *Object to load* empty to load the **first data frame or matrix in the order the objects were saved**, or type the name of the object you want.
- **Types**: numbers, text, logical values and date-times come through as they are. **Factors become text**; **dates (`Date`) become date-times at midnight UTC**; list fields become text, their values joined with commas.
- **Row names**: when a data frame has row names other than 1, 2, 3... (store codes, car models, gene names), they become a first field called **Row name**, so they are not lost.
- **Other objects**: a vector becomes one field, *Value* (with a *Name* field when the vector is named); a list of equal-length vectors becomes one field per element. Objects that are not tables, such as fitted models or functions, can't be loaded: the block stops and says what class the object is.

## Language and libraries

R, with the `tools` package (part of base R). Nothing to install.

## Inputs

None. The block is a source: it reads the file chosen in its options.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| R data file | `rda_file` | File | The .rds, .rda or .RData file to read, on the Omniscope server. |
| Object to load | `obj` | Text | For .rda and .RData files: the name of the object to load. Empty: the first data frame or matrix in the file. Not used for .rds files. |

## Outputs

- **Data** (`Output Data`): the chosen object as records.
- **Objects** (`Output Data 2`): one record per object in the file, in the order saved: Object (name), Class, Records and Fields (when it can be read as a table, else empty), Readable (whether it can be read as a table) and Loaded (whether it is the one on the Data output). For a .rds file the object is named after the file.

## Limits

- The whole file is read into memory. In tests, a 200,000-record .rds file loaded in under a second.
- Only one object is loaded per block; add a second block for another object (the Objects output lists them).
- Field names are kept as they are in R, except that empty names become `Field 1`, `Field 2`... and repeated names get a number (`a`, `a 1`).
- Time zones: date-times keep their instant; dates become midnight UTC.
- R data files can hold code as well as data. Read only files from sources you trust.

## Source

[script.R](script.R)

`sample-data/store-survey.RData` (three objects: a note, 24 invented survey responses and 4 stores) and `sample-data/stores.rds` are written by `sample-data/make-sample-data.R`. The data is invented. `sample-data/placeholder.csv` is the block's Data output for `store-survey.RData`, shown in the demo in place of the block (the demo server can't hold R data files); a test checks they match.
