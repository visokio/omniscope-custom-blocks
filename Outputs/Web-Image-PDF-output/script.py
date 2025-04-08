from omniscope.api import OmniscopeApi

from visokio_omniprint import ImagesPdf, Image, Tools

import pandas as pd


omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# read the value of the option called "my_option"
url_field = omniscope_api.get_option("url_field")
folder_path = omniscope_api.get_option("folder_path")
resolution = omniscope_api.get_option("resolution")
sleep_seconds = omniscope_api.get_option("sleep_seconds")
orientation = omniscope_api.get_option("orientation")
create_pdf = omniscope_api.get_option("create_pdf")
output_file_name = omniscope_api.get_option("pdf_file_name")
compressed = omniscope_api.get_option("compression")

tinify = omniscope_api.get_option("tinify")
tinify_key = omniscope_api.get_option("tinify_key")
tinify_width = omniscope_api.get_option("tinify_width")

is_docker = omniscope_api.is_docker()

auth_username = omniscope_api.get_option("auth_username")
auth_password = omniscope_api.get_option("auth_password")


screenshots = []
images_pdf = ImagesPdf()
image = Image()
tools = Tools()

for index, row in input_data.iterrows():
    url = row[url_field]
    
    url = tools.add_basic_auth(url, auth_username, auth_password)
    
    file_name = 'screenshot_'+str(index)+'.png'
    image_path = folder_path+'/'+file_name
    
    image.grab_screenshot_in_path(url, sleep_seconds, is_docker, image_path)
    
    if tinify:
        image.tinify(tinify_key, image_path, tinify_width)
    
    images_pdf.add_path(image_path)
    
    screenshots.append({"URL" : url, "Screenshot path" : image_path, "Screenshot filename" : file_name})
    
    
output_data = pd.DataFrame(screenshots)    
           

if create_pdf:
    pdf_path = folder_path + "/" + output_file_name
    images_pdf.create_pdf_in_path(pdf_path, orientation, resolution, compressed)
    output_data['PDF'] = pdf_path    



#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()