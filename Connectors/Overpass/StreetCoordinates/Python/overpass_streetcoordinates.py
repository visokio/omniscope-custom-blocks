import overpy
import time

api = overpy.Overpass()

# Info:
#  - https://python-overpy.readthedocs.io/en/latest/example.html#use-overpass-ql-or-overpass-xml
#  - http://overpass-turbo.eu/
#  - https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_API_by_Example#List_of_streets

address_field_name = 'Name of the address field'
output_data = pandas.DataFrame(columns=[address_field_name,'Path','Longitude','Latitude'])
i = 0
for index, row in input_data.iterrows():
    finished = False
    while not finished:
        try:
            result = api.query('way["name"~"'+row[address_field_name]+'"];(._;>;);out body;')
            for way in result.ways:
                for node in way.get_nodes():
                    output_data.loc[i] = [row[address_field_name], way.id, str(node.lon), str(node.lat)]
                    i += 1
            finished = True
        except overpy.exception.OverpassTooManyRequests:
            time.sleep(10)
