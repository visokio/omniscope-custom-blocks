import pandas as pd
from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()
import geopandas as gpd

# Load the GeoJSON file
gdf = gpd.read_file(omniscope_api.get_option("geojsonfile"))

# Calculate the centroids
gdf['centroid'] = gdf.geometry.centroid

# Create a new DataFrame with the country names (using 'nuts118nm') and their centroids

shapeIDfield = omniscope_api.get_option("shapeIDfield")

result = gdf[[shapeIDfield, 'centroid']].copy()

# Rename the columns for clarity
result.columns = [shapeIDfield, 'centroid_point']

# Split the centroid into latitude and longitude
result['Lat'] = result['centroid_point'].y
result['Long'] = result['centroid_point'].x

# Drop the centroid_point column
result = result[[shapeIDfield, 'Lat', 'Long']]
result

omniscope_api.write_output_records(result, output_number=0)
omniscope_api.close()