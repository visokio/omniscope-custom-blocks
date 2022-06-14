from omniscope.api import OmniscopeApi
from urllib.parse import unquote
import subprocess
import shlex
import os
import pandas as pd

omniscope_api = OmniscopeApi()
    
command = omniscope_api.get_option("command")

ignoreErrors = omniscope_api.get_option("ignoreErrors")

isPosix = False
if os.name == 'posix':
    isPosix = True

result = subprocess.run(shlex.split(command,posix=isPosix), capture_output=True)

if (result.returncode != 0):
    print(result)
    if (ignoreErrors):
        omniscope_api.update_message("Command failed, but ignored. Return code:"+str(result.returncode)+". Check execution logs.");
    else:
        omniscope_api.abort(message="Command failed. Return code:"+str(result.returncode)+". Check execution logs.")

output_data_2 = pd.DataFrame(data=[result.stdout], columns=['Output'])

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)
output_data = input_data

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)

if output_data_2 is not None:
    omniscope_api.write_output_records(output_data_2, output_number=1)
    
omniscope_api.close()