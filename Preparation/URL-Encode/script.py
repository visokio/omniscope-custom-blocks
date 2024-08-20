from omniscope.api import OmniscopeApi
import pandas
import urllib.parse

omniscope_api = OmniscopeApi()

fieldName = omniscope_api.get_option("fieldName")

def handle_chunk(chunk):
    chunk["Quoted text"] = chunk[fieldName].map(lambda x: urllib.parse.quote(x))
    
    return (chunk)

# process the data stream, by applying a lambda function to each data chunk
omniscope_api.process_stream(handle_chunk)

# the data stream is over. No other data can be read or written.
omniscope_api.close()