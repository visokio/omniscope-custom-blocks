# Overpass Street Coordinates

Finds all matching streets given a street name and requests multiple coordinates along the street using data from [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API).
It will create a row for each point found that is part of a street that matches the given street name.
The resulting rows will include the street name, the street Id and the coordinates of the point.
The script needs an input with a field with the street name.

## Language
Python3

## Input fields
 - Address: Street name used to query coordinates.

## Output fields
 - Address: Street name from the input used for the query.
 - Path: Id of the street that matches the given name.
 - Longitude: Longitude value of the point in the street.
 - Latitude: Latitude value of the point in the street.

## Parameters
 - address_field_name: The name of the address field.

## Dependencies
overpy, time

## Source
[overpass_streetcoordinates](https://github.com/visokio/omniscope-custom-blocks/blob/master/Connectors/Overpass/StreetCoordinates/Python/overpass_streetcoordinates.py)

## Resources
 - [Overpy docs](https://python-overpy.readthedocs.io/en/latest/example.html#use-overpass-ql-or-overpass-xml)
 - [Overpass Turbo](http://overpass-turbo.eu/)
 - [Overpass API examples](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_API_by_Example#List_of_streets)
