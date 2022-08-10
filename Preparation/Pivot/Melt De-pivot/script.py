from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

fixed_fields = omniscope_api.get_option("fixed_fields")
var_name = omniscope_api.get_option("var_name")
value_name = omniscope_api.get_option("value_name")


def process(chunk):
    result = chunk.melt(id_vars=fixed_fields, var_name=var_name, value_name=value_name)
    return (result)

# process the data stream, by applying a lambda function to each data chunk
omniscope_api.process_stream(process)

# the data stream is over. No other data can be read or written.
omniscope_api.close()