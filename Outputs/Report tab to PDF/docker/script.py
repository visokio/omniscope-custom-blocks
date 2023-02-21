from omniscope.api import OmniscopeApi
from urllib.parse import unquote
import shlex
import pandas as pd
import os

import sys
import json
import base64

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import staleness_of
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

omniscope_api = OmniscopeApi()

if not omniscope_api.is_docker(): abort("This script can only be used in DOCKER mode. You are running in HOST mode, please use the other community block called 'Report Tab to PDF'")


def send_devtools(driver, cmd, params={}):
    resource = "/session/%s/chromium/send_command_and_get_result" % driver.session_id
    url = driver.command_executor._url + resource
    body = json.dumps({"cmd": cmd, "params": params})
    response = driver.command_executor._request("POST", url, body)

    if not response:
        raise Exception(response.get("value"))

    return response.get("value")


def get_pdf(path: str, timeout: int):
    webdriver_options = Options()
    webdriver_prefs = {}
    driver = None

    webdriver_options.add_argument("--headless")
    webdriver_options.add_argument("--disable-gpu")
    webdriver_options.add_argument("--no-sandbox")
    webdriver_options.add_argument("--disable-dev-shm-usage")
    webdriver_options.add_argument("--window-size=1920,1080")
    webdriver_options.experimental_options["prefs"] = webdriver_prefs

    webdriver_prefs["profile.default_content_settings"] = {"images": 2}

    driver = webdriver.Chrome(ChromeDriverManager().install(), options=webdriver_options)

    driver.get(path)

    try:
        WebDriverWait(driver, timeout).until(
            staleness_of(driver.find_element(by=By.TAG_NAME, value="html"))
        )
    except TimeoutException:
        calculated_print_options = {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
        }
        
        result = send_devtools(
            driver, "Page.printToPDF", calculated_print_options)
        driver.quit()
        return base64.b64decode(result["data"])






report_url_field = omniscope_api.get_option("report")
file_name_field = omniscope_api.get_option("fileName")
output_folder = omniscope_api.get_option("outputFolder")
chrome_delay = omniscope_api.get_option("chromeDelay")

if chrome_delay is None:
    chrome_delay = 3

page_size = ""
page_width = omniscope_api.get_option("pageWidth")
if (page_width is not None and page_width > 0):
   page_size = "&pageWidth="+str(page_width)

page_height = omniscope_api.get_option("pageHeight")
if (page_height is not None and page_height > 0):
   page_size += "&pageHeight="+str(page_height)




# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)


if (output_folder.endswith('/')):
    output_folder = output_folder[:-1]




pdfs = []


for index, row in input_data.iterrows():
    report = row[report_url_field]
    report_name = report.rsplit('/', 3)[-2]
    report_base_url = report.rsplit('/', 1)[-2]
    tab_name_with_filter = report.rsplit('#', 1)[-1]
    report_url = report_base_url + "/" + "#device=printer"+ page_size +"&tab=" + tab_name_with_filter
    tab_name = unquote(tab_name_with_filter)

    if ('&' in tab_name):
        tab_name = tab_name.split('&',2)[0]
    file_name = report_name + "-" + tab_name + "-" + str(index) + ".pdf"
    if (file_name_field is not None):
        file_name = row[file_name_field] + ".pdf"
    file_path = output_folder + "/" + file_name
    
    pdf = get_pdf(report_url, chrome_delay)
    
    with open(file_path, "wb") as file:
        file.write(pdf)
    
    pdfs.append({"URL" : report, "PDF filename" : file_name})


output_data = pd.DataFrame(pdfs)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()