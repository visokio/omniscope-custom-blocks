from omniscope.api import OmniscopeApi
import os, pandas
from azure.storage.blob import BlobServiceClient

omniscope_api = OmniscopeApi()

connectionString = omniscope_api.get_option("connectionString")

blob_service_client = BlobServiceClient.from_connection_string(connectionString)

# Instantiate a new ContainerClient
containerName = omniscope_api.get_option("containerName")
container_client = blob_service_client.get_container_client(containerName)

# Instantiate a new BlobClient
blobPath = omniscope_api.get_option("blobPath")
blob_client = container_client.get_blob_client(blobPath)

blobFileName = os.path.basename(blobPath)

with open(blobFileName, "wb") as my_blob:
  download_stream = blob_client.download_blob()
  my_blob.write(download_stream.readall())
  print(omniscope_api.get_option("fileType"))
  if (omniscope_api.get_option("fileType") == "Parquet"):
     output_data = pandas.read_parquet(blobFileName)
  else:
     output_data = pandas.read_csv(blobFileName)
     booleanDictionary = {True: 'TRUE', False: 'FALSE'}
     output_data = output_data.replace(booleanDictionary)


#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()