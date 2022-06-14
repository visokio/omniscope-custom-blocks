from omniscope.api import OmniscopeApi
import subprocess
import pandas as pd
import os

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# read the value of the option called "my_option"
omniprint = omniscope_api.get_option("omniprint")

report = omniscope_api.get_option("report")
reportName = report.rsplit('/', 2)[-2]
reportBaseUrl = report.rsplit('/', 1)[-2]
tabName = report.rsplit('#', 1)[-1]

outputFolder = omniscope_api.get_option("outputFolder")
if (outputFolder.endswith('/')):
    outputFolder = outputFolder[:-1]
chromePort = omniscope_api.get_option("chromePort")
if (chromePort is None or chromePort < 1):
    chromePort = 9998   
chromeDelay = omniscope_api.get_option("chromeDelay")
if (chromeDelay is None or chromeDelay < 1):
    chromeDelay = 3000

    
chrome = omniscope_api.get_option("googleChrome")
chromeCommand = chrome + " --headless --disable-gpu --disable-translate " \
"--disable-extensions --disable-background-networking --safebrowsing-disable-auto-update " \
"--disable-sync  --metrics-recording-only --disable-default-apps --no-first-run --mute-audio " \
"--hide-scrollbars --remote-debugging-port="+str(chromePort)+" --window-size=1920,1080"

pdfs = []

process = None

try:
  process = subprocess.Popen(chromeCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE) 

  for index, row in input_data.iterrows():
    reportUrl = reportBaseUrl + "/" + "#device=printer&tab=" + tabName
    scenarioId = row["scenario"]
    if (scenarioId is not None and type(scenarioId) == str):
        reportUrl = reportBaseUrl + "/s/" + scenarioId + "/" + "#device=printer&tab=" + tabName
        filename = outputFolder + "/" + reportName + "-" + scenarioId + ".pdf"
        subprocess.run([omniprint, reportUrl, filename, str(chromePort), str(chromeDelay)])
        pdfs.append({"URL" : reportUrl, "PDF" : filename})

finally:
  if (process):
    process.kill()
    
output_data = pd.DataFrame(pdfs)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()