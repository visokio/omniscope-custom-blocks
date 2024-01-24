from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

fixed_fields = omniscope_api.get_option("fixed_fields")
var_name = omniscope_api.get_option("var_name")
value_name = omniscope_api.get_option("value_name")

input_data = omniscope_api.read_input_records(input_number=0)


def process(chunk):
    result = chunk.melt(id_vars=fixed_fields, var_name=var_name, value_name=value_name)
    return (result)

output_data = process(input_data)

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()