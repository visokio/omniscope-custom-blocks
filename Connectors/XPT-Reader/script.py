from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

import xport.v56
import pandas as pd

# read the value of the option called "my_option"
xptFile = omniscope_api.get_option("xptFile")


def read_xpt_to_dataframes(file_path):
    with open(file_path, 'rb') as f:
    
        datasetName = omniscope_api.get_option("datasetName")             
        library = xport.v56.load(f)
        
        # Get dataset names and their respective concatenated fields
        summary_data = [(dataset_name, ", ".join(dataset_content.columns)) 
                        for dataset_name, dataset_content in library.items()]
        
        summary_df = pd.DataFrame(summary_data, columns=['Dataset Name', 'Fields'])
                
        # Load the first dataset into a DataFrame
        if (datasetName is None):
            datasetName = list(library.keys())[0]   #use first
       
        data_df = library.get(datasetName, None)  # returns None if the dataset_name doesn't exist

    return summary_df, data_df

# Usage example
summary_df, data_df = read_xpt_to_dataframes(xptFile)

if summary_df is not None:
    omniscope_api.write_output_records(summary_df, output_number=0)
if data_df is not None:
    omniscope_api.write_output_records(data_df, output_number=1)
else: 
    omniscope_api.abort("Dataset name does not exist. Leave the option empty to load the first dataset.")

omniscope_api.close()