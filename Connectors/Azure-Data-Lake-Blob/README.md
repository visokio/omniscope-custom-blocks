# Azure Data Lake Storage Gen2 Blob

Reads one CSV or Parquet file (blob) from a container in an Azure storage account, including Data Lake Storage Gen2, using the account's connection string.

Files landed in Azure storage by other systems (nightly exports, data lake zones, application logs) can be read straight into a workflow, without copying them to the Omniscope server first.

- Give the storage account's **connection string**, the **container** and the **blob path** (folders and file name, for example `sales/2026/march.parquet`). Works with Data Lake Storage Gen2 accounts and ordinary Blob storage accounts.
- The **file type** is taken from the extension by default: `.parquet` or `.pq` for Parquet, `.csv` or `.txt` for comma-separated, `.tsv` for tab-separated, each optionally followed by `.gz` (gzip). Or choose CSV or Parquet.
- CSV files need a header row; values are typed by pandas (numbers, `True`/`False` as true/false, the rest as text).
- Parquet types Omniscope has no field type for are converted: categories to text, decimals to decimal numbers, durations to seconds, lists and structs to JSON text, binary to hexadecimal text.
- The file is read in memory; nothing is saved on the Omniscope server.
- A connection string from Access keys holds the account key, which gives full read and write access to every container in the storage account, and it is saved in the project with the block's options. The block only reads, so where your organisation allows it, use a connection string with a shared access signature (SAS) limited to reading the container.

## Inputs
None. The block reads from Azure storage.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Connection string | `connectionString` | Password | The storage account's connection string: in the Azure portal, Security + networking > Access keys, Connection string under key1. |
| Container name | `containerName` | Text | The blob container (for Data Lake Storage Gen2, the file system). Case-sensitive. |
| Blob path | `blobPath` | Text | The folders and file name inside the container, for example `sales/2026/march.parquet`. Case-sensitive. |
| File type | `fileType` | Choice | Automatic (from the extension), CSV or Parquet. Default: Automatic. |

## Outputs
- **Data** (`Output Data`): the file's records, with the fields in the file. A CSV file with only a header row gives its fields and no records.

## Errors
A missing container or blob, a wrong connection string or an unreadable file stops the block with a message, for example "Could not read retail/sales/none.csv: ResourceNotFoundError: The specified blob does not exist. Check the container name and the blob path (they are case-sensitive)." An empty file stops it with "... is empty".

## Size of input
The whole file is held in memory twice while it is read (the downloaded bytes and the table). In tests, a 300,000-record Parquet file was read and converted in well under a second once downloaded; download time depends on the network.

<!--language-->
## Language and libraries

Python. It uses pandas, numpy, azure-storage-blob and pyarrow.

pandas and numpy are part of Omniscope's Python environment. azure-storage-blob (MIT licence) and pyarrow (Apache License 2.0) are listed in the manifest's dependencies; Omniscope installs them on first run if they are missing.
<!--/language-->

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented: `placeholder.csv` is a file the block would read (and outputs unchanged).
