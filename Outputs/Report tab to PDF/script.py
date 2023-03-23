from omniscope.api import OmniscopeApi
from urllib.parse import unquote
import shlex
import pandas as pd
import os

import sys
import json
import base64

from visokio_omniprint import Pdf, Tools

omniscope_api = OmniscopeApi()

report_url_field = omniscope_api.get_option("report")
file_name_field = omniscope_api.get_option("fileName")
output_folder = omniscope_api.get_option("outputFolder")
chrome_delay = omniscope_api.get_option("chromeDelay")

is_docker = omniscope_api.is_docker()

if chrome_delay is None:
    chrome_delay = 3

page_width = omniscope_api.get_option("pageWidth")
page_height = omniscope_api.get_option("pageHeight")

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

if (output_folder.endswith('/')):
    output_folder = output_folder[:-1]


pdf_creator = Pdf()
tools = Tools()

pdfs = []

for index, row in input_data.iterrows():
    url = row[report_url_field]
    file_name = None
    
    print ("FILE NAME:"+str(file_name_field)+":")
    
    if file_name_field is not None and len(file_name_field) > 0:
    	file_name = row[file_name_field]
    
    report_url, file_path, file_name = tools.report_url(url, page_width, page_height, output_folder, file_name, index)
    pdf = pdf_creator.create_pdf(report_url, chrome_delay, is_docker)
    
    with open(file_path, "wb") as file:
        file.write(pdf)
    
    pdfs.append({"URL" : url, "PDF filename" : file_name})

output_data = pd.DataFrame(pdfs)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()