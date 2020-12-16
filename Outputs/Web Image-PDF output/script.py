from omniscope.api import OmniscopeApi
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from fpdf import FPDF

import fpdf
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
        
    if (omniscope_api.get_option("createPdf")):
        outputFileName = omniscope_api.get_option("pdfFileName")
        if (outputFileName is None):
            outputFileName = 'output.pdf'
        
        pdf = FPDF(orientationOpt, 'pt', (int(resSplit[0]),int(resSplit[1])))
        pdf.set_margins(0,0,0)
        pdf.set_auto_page_break(False)
        pdf.set_compression(omniscope_api.get_option("compression"))
        
        for image in pngGrabbed:
           pdf.add_page()
           pdf.image(image)
           
        pdfPath = folderPath + "/" + outputFileName
        
        if os.path.exists(pdfPath):
            os.remove(pdfPath)
        pdf.output(pdfPath, "F")
    
finally:
    driver.quit()

output_data = pd.DataFrame(screenshots)
if (omniscope_api.get_option("createPdf")):
    output_data['PDF'] = pdfPath

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()
