from omniscope.api import OmniscopeApi
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.files.file import File


import os, pandas

omniscope_api = OmniscopeApi()

print (omniscope_api.file_name + " <--- project location")

scriptFolder = os.path.dirname(os.path.realpath(__file__))
print(scriptFolder + " <--- script folder location")

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# read the value of the option called "my_option"
# my_option = omniscope_api.get_option("my_option")    
        
username = omniscope_api.get_option("username")
password = omniscope_api.get_option("password")
fileUrl = omniscope_api.get_option("fileUrl")

downloadedFileName = os.path.basename(fileUrl)

def download_file():
    user_credentials = UserCredential(username, password)
    with open(downloadedFileName, 'wb') as local_file:
        file = File.from_url(fileUrl).with_credentials(user_credentials).download(local_file).execute_query()
        print ("File from "+fileUrl+ " downloaded locally to "+scriptFolder+"/"+downloadedFileName)


download_file()
  

output_data = pandas.DataFrame(columns={"File downloaded"})
output_data.loc[0] = os.path.join(scriptFolder,downloadedFileName)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()
