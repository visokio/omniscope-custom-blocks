import numpy as np
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

partition_size = omniscope_api.get_option("partition_size")
if partition_size is None or int(partition_size) < 1:
    omniscope_api.abort("\"Number of records per partition\" must be a whole number of 1 or more.")
partition_size = int(partition_size)

records_seen = 0  # records in earlier chunks: numbering carries on across the stream


def handle_chunk(chunk):
    global records_seen
    positions = np.arange(records_seen, records_seen + len(chunk), dtype="int64")
    records_seen += len(chunk)
    # an existing Partition field is replaced
    chunk["Partition"] = positions // partition_size + 1
    chunk["Partition"] = chunk["Partition"].astype("Int64")
    return chunk


# process the data stream, applying the function to each chunk of records in turn
omniscope_api.process_stream(handle_chunk)

# the data stream is over. No other data can be read or written.
omniscope_api.close()
