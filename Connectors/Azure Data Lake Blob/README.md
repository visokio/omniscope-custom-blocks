# Azure Data Lake Gen2 Blob Connector
### Opens and loads a CSV or Parquet blob / file from an Azure Data Lake (Gen2) blob container.
#### Instructions:
1. Copy your credentials from the Azure portal
1.1 Sign in to the Azure portal.
1.2 Locate your storage account.
1.3 In the Settings section of the storage account overview, select Access keys. 
1.4 Find the Connection string value under key1, and select the Copy button to copy the connection string and paste in this block config.

2. Insert the Blob Container name

3. Insert the Blob/File path *(e.g. myfolder/myfile.parquet)* to download from the Data Lake and load its data in this block.

## Language
Python

## Dependencies
azure-storage-blob pyarrow

## Source
[script.py](https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Azure%20Data%20Lake%20Blob/script.py)
