from omniscope.api import OmniscopeApi
import pandas as pd

from visokio_omniprint import Pdf, Tools

omniscope_api = OmniscopeApi()

base_report_url = omniscope_api.get_option("report")
output_folder = omniscope_api.get_option("outputFolder")
chrome_delay = omniscope_api.get_option("chromeDelay")

auth_username = omniscope_api.get_option("auth_username")
auth_password = omniscope_api.get_option("auth_password")


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

    scenario_id = row["scenario"]
    
    report_url, file_path, file_name = tools.scenario_report_url(base_report_url, scenario_id, page_width, page_height, output_folder, auth_username, auth_password)
    
    pdf = pdf_creator.create_pdf(report_url, chrome_delay, is_docker)
    
    with open(file_path, "wb") as file:
        file.write(pdf)
    
    pdfs.append({"URL" : report_url, "PDF filename" : file_name})

output_data = pd.DataFrame(pdfs)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()