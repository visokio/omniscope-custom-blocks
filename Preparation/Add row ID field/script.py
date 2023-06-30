from omniscope.api import OmniscopeApi
import pandas
omniscope_api = OmniscopeApi()

chunkno = 0
fieldName = omniscope_api.get_option("fieldName")

def handle_chunk(chunk):

    global chunkno
    global fieldName
    chunk[fieldName] = chunk.index + 1 + (chunkno * len(chunk.index))
    chunkno +=1
    return (chunk)

# process the data stream, by applying a lambda function to each data chunk
omniscope_api.process_stream(handle_chunk)

# the data stream is over. No other data can be read or written.
omniscope_api.close()
