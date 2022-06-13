from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

partition_size = omniscope_api.get_option("partition_size")

it = 0
part = 1


def partition(row):
    global it
    global part
    
    it = it + 1
    if it > partition_size:
        part = part + 1
        it = 1
        
    return (str(part))

def handle_chunk(chunk):
    chunk["Partition"] = chunk.apply(lambda row: partition(row), axis = 1)
    return (chunk)


# process the data stream, by applying a lambda function to each data chunk
omniscope_api.process_stream(handle_chunk)

# the data stream is over. No other data can be read or written.
omniscope_api.close()