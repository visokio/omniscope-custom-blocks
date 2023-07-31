from omniscope.api import OmniscopeApi
import pandas as pd
import yfinance as yf

omniscope_api = OmniscopeApi()

tickerField = omniscope_api.get_option("Ticker")
startDate = omniscope_api.get_option("Start")
endDate = omniscope_api.get_option("End")
interval = omniscope_api.get_option("Interval")

block_input = omniscope_api.read_input_records(input_number=0)
outputData = pd.DataFrame();
for index, row in block_input.iterrows():
    outputFrame = yf.Ticker(row[tickerField]).history(start=startDate, end=endDate, interval=interval)
    outputFrame = outputFrame.reset_index()
    new_cols = list(block_input.columns.values)
    outputFrame[new_cols] = row.values.tolist();
    outputData = pd.concat([outputData, outputFrame])


#write the output records in the first output
if outputData is not None:
    omniscope_api.write_output_records(outputData, output_number=0)
omniscope_api.close()