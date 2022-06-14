from omniscope.api import OmniscopeApi
from PyPDF2 import PdfFileMerger
import glob

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# read the value of the option called "my_option"
# my_option = omniscope_api.get_option("my_option")

title = omniscope_api.get_option("title")
pdfPath = omniscope_api.get_option("pdfPath")
outputFolder = omniscope_api.get_option("outputFolder")

merger = PdfFileMerger()

for index, row in input_data.iterrows():
    pdf = row[pdfPath]    
    merger.append(pdf, row[title] if title is not None and title != "" else None)

outputFile = outputFolder+"/"+omniscope_api.get_option("fileName")

merger.write(outputFile)
merger.close()

output_data = input_data
output_data['Combined PDF'] = outputFile

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()