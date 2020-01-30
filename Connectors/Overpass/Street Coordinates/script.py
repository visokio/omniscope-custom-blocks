from omniscope.api import OmniscopeApi
import pandas

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

### Info
#  - https://python-overpy.readthedocs.io/en/latest/example.html#use-overpass-ql-or-overpass-xml
#  - http://overpass-turbo.eu/
#  - https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_API_by_Example#List_of_streets

### Input fields
address_field_name = omniscope_api.get_option("addressField")

### Script
import overpy
import time

# sanity checks
if (is.null(input.data)) omniscope_api.abort("No input data")

api = overpy.Overpass()

# Define output columns
output_data = pandas.DataFrame(columns=[address_field_name,'Path','Longitude','Latitude'])

i = 0
for index, row in input_data.iterrows():
    finished = False
    while not finished:
        try:
            # Find all the streets that match the given name
            result = api.query('way["name"~"'+row[address_field_name]+'"];(._;>;);out body;')
            for way in result.ways:
                # For each street found, create a new output row for each point with the street Id, Lat and Lon
                for node in way.get_nodes():
                    output_data.loc[i] = [row[address_field_name], way.id, str(node.lon), str(node.lat)]
                    i += 1
            finished = True
        # Catch exception when too many requests and wait 10 seconds before repeating the query
        except overpy.exception.OverpassTooManyRequests:
            time.sleep(10)


#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()
