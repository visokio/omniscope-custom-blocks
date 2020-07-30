from omniscope.api import OmniscopeApi
import pysftp, pandas, os

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# UNSAFE BUT IF YOUR SERVER DOES NOT HAVE A VALID HOST SSH KEYS FOR THE SFTP SERVER THAT'S HOW TO IGNORE THAT.
cnopts = pysftp.CnOpts()
cnopts.hostkeys = None   

myHostname = omniscope_api.get_option("hostname")
myPort = omniscope_api.get_option("port")
myUsername = omniscope_api.get_option("username")
myPassword = omniscope_api.get_option("password")
extension = omniscope_api.get_option("extension")

scriptFolder = os.path.dirname(os.path.realpath(__file__))
print(scriptFolder + " <--- script folder location")


files = []
filenames = []
with pysftp.Connection(host=myHostname, username=myUsername, password=myPassword, port=myPort, cnopts=cnopts) as sftp:

    # Switch to a remote directory
    sftp.cwd(omniscope_api.get_option("folder"))

    # Get structure of the dir
    directory_structure = sftp.listdir_attr()

    for attr in directory_structure:
        filepath = attr.filename
        if (extension is None or filepath.endswith(extension)):
            localFilePath = scriptFolder+"/"+filepath
            sftp.get(filepath, localFilePath)
            print("File "+filepath+ " downloaded locally to "+localFilePath)
            files.append(localFilePath)
            filenames.append(filepath)

d = {"files":files , "filenames": filenames}
output_data = pandas.DataFrame(d)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()