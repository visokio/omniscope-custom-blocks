from omniscope.api import OmniscopeApi
from urllib.parse import unquote
import subprocess
import shlex
import pandas as pd
import os

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# read the value of the option called "my_option"
omniprint = omniscope_api.get_option("omniprint")

outputFolder = omniscope_api.get_option("outputFolder")
if (outputFolder.endswith('/')):
    outputFolder = outputFolder[:-1]
chromePort = omniscope_api.get_option("chromePort")
if (chromePort is None or chromePort < 1):
    chromePort = 9998   
chromeDelay = omniscope_api.get_option("chromeDelay")
if (chromeDelay is None or chromeDelay < 1):
    chromeDelay = 3000

setFileName = omniscope_api.get_option("fileName")
    
chrome = omniscope_api.get_option("googleChrome")
chromeCommand = chrome + " --headless --disable-gpu --disable-translate " \
"--disable-extensions --disable-background-networking --safebrowsing-disable-auto-update " \
"--disable-sync  --metrics-recording-only --disable-default-apps --no-first-run --mute-audio " \
"--hide-scrollbars --remote-debugging-port="+str(chromePort)+" --window-size=1920,1080"

pageSize = ""
pageWidth = omniscope_api.get_option("pageWidth")
if (pageWidth is not None and pageWidth > 0):
   pageSize = "&pageWidth="+str(pageWidth)

pageHeight = omniscope_api.get_option("pageHeight")
if (pageHeight is not None and pageHeight > 0):
   pageSize += "&pageHeight="+str(pageHeight)

isPosix = False
if os.name == 'posix':
    isPosix = True

pdfs = []

process = None

try:
  process = subprocess.Popen(shlex.split(chromeCommand,posix=isPosix), stdout=subprocess.PIPE, stderr=subprocess.PIPE) 

  for index, row in input_data.iterrows():
    report = row[omniscope_api.get_option("report")]
    reportName = report.rsplit('/', 3)[-2]
    reportBaseUrl = report.rsplit('/', 1)[-2]
    tabNameWithFilter = report.rsplit('#', 1)[-1]
    reportUrl = reportBaseUrl + "/" + "#device=printer"+ pageSize +"&tab=" + tabNameWithFilter
    tabName = unquote(tabNameWithFilter)
    print(tabName)
    if ('&' in tabName):
        tabName = tabName.split('&',2)[0]
    filename = reportName + "-" + tabName + "-" + str(index) + ".pdf"
    if (setFileName is not None):
        filename = row[setFileName] + ".pdf"
    filepath = outputFolder + "/" + filename
    subprocess.run([omniprint, reportUrl, filepath, str(chromePort), str(chromeDelay)])
    print(reportUrl)
    pdfs.append({"URL" : report, "PDF path" : filepath, "PDF filename" : filename})

finally:
  if (process):
    process.kill()
    
output_data = pd.DataFrame(pdfs)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()