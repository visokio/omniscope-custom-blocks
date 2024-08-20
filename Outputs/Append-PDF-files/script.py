from omniscope.api import OmniscopeApi
from PyPDF2 import PdfMerger
import glob

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

#input
input_folder = omniscope_api.get_option("input_folder")
pdf_file_names = omniscope_api.get_option("pdf_file_names")
title = omniscope_api.get_option("title")

#output
output_folder = omniscope_api.get_option("output_folder")
file_name = omniscope_api.get_option("file_name")

merger = PdfMerger()

for index, row in input_data.iterrows():
    pdf = input_folder + "/" + row[pdf_file_names]    
    merger.append(pdf, row[title] if title is not None and title != "" else None)

output_file = output_folder + "/" + file_name

merger.write(output_file)
merger.close()

output_data = input_data
output_data['Combined PDF'] = file_name

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()