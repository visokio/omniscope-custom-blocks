from omniscope.api import OmniscopeApi
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import pandas as pd
import time, os

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# read the value of the option called "my_option"
urlField = omniscope_api.get_option("urlField")
folderPath = omniscope_api.get_option("folderPath")
resolution = omniscope_api.get_option("resolution")
sleepSeconds = omniscope_api.get_option("sleepSeconds")
orientationOpt = omniscope_api.get_option("orientationOpt")

resSplit = resolution.split("x")
#width, then height
imgSize = [ int(resSplit[0]), int(resSplit[1]) ]

if orientationOpt == "P":
    resolution = resSplit[1]+"x"+resSplit[0]
    imgSize = [ int(resSplit[1]), int(resSplit[0]) ]

#Pdf lib wants heigth than width 
resSplit[0], resSplit[1] = resSplit[1], resSplit[0]
    
try:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size="+resolution)

    chrome_driver = omniscope_api.get_option("chromeDriver")
    driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=chrome_driver)

    screenshots = []
    pngGrabbed = []

    for index, row in input_data.iterrows():
        url = row[urlField]
        driver.get(url)
        
        time.sleep(sleepSeconds)
        
        fileName = 'screenshot_'+str(index)+'.png'
        imagePath = folderPath+'/'+fileName
        
        if os.path.exists(imagePath):
            os.remove(imagePath)
        
        screenshot = driver.save_screenshot(imagePath)
        pngGrabbed.append(imagePath)
        screenshots.append({"URL" : url, "Screenshot path" : imagePath, "Screenshot filename" : fileName})
        
    
    outputFileName = omniscope_api.get_option("pptxFileName")
    if (outputFileName is None):
        outputFileName = 'output.pptx'
        
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    for image in pngGrabbed:
        blank_slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank_slide_layout)
        left = top = Inches(0)
        pic = slide.shapes.add_picture(image, left, top, Inches(10))
     
    pptxPath = folderPath + "/" + outputFileName
    prs.save(pptxPath)
    
    if (not omniscope_api.get_option("keepScreenshots")):
        for image in pngGrabbed:
            os.remove(image)
    
finally:
    driver.quit()

output_data = pd.DataFrame(screenshots)
output_data['PPTX'] = pptxPath

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
    omniscope_api.close(message=outputFileName+" successfully created")
else:
    omniscope_api.close()