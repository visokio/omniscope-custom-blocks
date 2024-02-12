from omniscope.api import OmniscopeApi
from visokio_omniprint import ImagesPPTX, Image, Tools
from pptx import Presentation
from pptx.util import Inches
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
output_file_name = omniscope_api.get_option("output_file_name")

tinify = omniscope_api.get_option("tinify")
tinify_key = omniscope_api.get_option("tinify_key")
tinify_width = omniscope_api.get_option("tinify_width")

is_docker = omniscope_api.is_docker()

screenshots = []
images_pptx = ImagesPPTX()
image = Image()

for index, row in input_data.iterrows():
    url = row[url_field]
    
    file_name = 'screenshot_'+str(index)+'.png'
    image_path = folder_path+'/'+file_name
    
    image.grab_screenshot_in_path(url, sleep_seconds, is_docker, image_path)
    
    if tinify:
        image.tinify(tinify_key, image_path, tinify_width)
    
    images_pptx.add_path(image_path)
    
    screenshots.append({"URL" : url, "png" : file_name})
    
    
output_data = pd.DataFrame(screenshots)    
           

pptx_path = folder_path + "/" + output_file_name
images_pptx.create_pptx_in_path(pptx_path, orientation, resolution)
output_data['PPTX'] = pptx_path    



#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()