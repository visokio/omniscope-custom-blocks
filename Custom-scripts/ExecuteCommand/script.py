from omniscope.api import OmniscopeApi
from urllib.parse import unquote
import subprocess
import shlex
import os
import pandas as pd

omniscope_api = OmniscopeApi()
    
command = omniscope_api.get_option("command")

ignore_errors = omniscope_api.get_option("ignoreErrors")
auto_cmd = omniscope_api.get_option("auto_cmd")
commands_field = omniscope_api.get_option("commands_field")

input_data = omniscope_api.read_input_records(input_number=0)

def get_commands(data, commands_field, auto_cmd):
    cmds = []
    for index, row in data.iterrows():
        cmd = row[commands_field]
        if auto_cmd:
            cmds.append("cmd /c " + cmd)
        else:
            cmds.append(cmd)
    return cmds
    
    
cmds = []
if commands_field is not None:
    cmds = get_commands(input_data, commands_field, auto_cmd)
else:
    if auto_cmd:
        cmds.append("cmd /c " + command)
    else:
        cmds.append(command)

isPosix = False
if os.name == 'posix':
    isPosix = True
    
stdout = []
stderr = []
codes = []
for cmd in cmds:

    result = subprocess.run(shlex.split(cmd,posix=isPosix), capture_output=True)

    if (result.returncode != 0):
    
        if (ignoreErrors):
            omniscope_api.update_message("Command failed, but ignored. Return code:"+str(result.returncode)+". Check execution logs.");
        else:
            omniscope_api.abort(message="Command failed. Return code:"+str(result.returncode)+". Check execution logs.")
    codes.append(result.returncode)
    stderr.append(result.stderr.decode("utf-8"))
    stdout.append(result.stdout.decode("utf-8"))

output_data_2 = pd.DataFrame({"cmd": cmds, "code": codes, "stdout": stdout, "stderr": stderr})

# read the records associated to the first block input

output_data = input_data

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)

if output_data_2 is not None:
    omniscope_api.write_output_records(output_data_2, output_number=1)
    
omniscope_api.close()