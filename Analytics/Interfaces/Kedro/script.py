from omniscope.api import OmniscopeApi
import pandas

omniscope_api = OmniscopeApi()

# read the records associated to the first block input


import importlib
import sys
import os


path = omniscope_api.get_option("path")

os.chdir(path)

sys.path.append(str(path))

temp = sys.stderr

sys.stderr = sys.stdout




def connect_input(index):
    input_name = None
    try:
        input_name = omniscope_api.get_option("input"+str(index))
    except:
        return
    if input_name is None or len(input_name) == 0:
        return
        
    input_path = path+"/data/01_raw/"+input_name+".csv"
    input_data_set = omniscope_api.read_input_records(input_number=index)
    if input_data_set is None:
        return
    os.remove(input_path)
    input_data_set.to_csv(input_path, index=False)

def connect_output(index):
    output_name = None
    try:
        output_name = omniscope_api.get_option("output"+str(index))
    except:
        return
    if output_name is None or len(output_name) == 0:
        return
        
    output_path = path+"/data/08_reporting/"+output_name+".csv"
    output_data_set = pandas.read_csv(output_path)
    if output_data_set is None:
        return
        
    omniscope_api.write_output_records(output_data_set, output_number=index)



i = 0

for i in range(0,20):
    connect_input(i)

kedro_cli = importlib.import_module("kedro_cli")

try:
    kedro_cli.run()
except:
    # ignore
    pass


for i in range(0,2):
    connect_output(i)

omniscope_api.close()