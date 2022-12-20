from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()



import fiona
import geopandas as gp
import pandas as pd


shp_file = omniscope_api.get_option("shp_file")
lat_field = omniscope_api.get_option("latitude_field")
lon_field = omniscope_api.get_option("longitude_field")
label = omniscope_api.get_option("label")
geometry = omniscope_api.get_option("geometry")

shp = gp.read_file(shp_file)
shp_length = len(shp.index)

omniscope_api.write_output_records(shp, output_number=1)

if label is None or geometry is None or lat_field is None or lon_field is None:
	omniscope_api.close()
else:
    input_data = pd.DataFrame(omniscope_api.read_input_records(input_number=0))
    output_data = input_data.copy()
    df = input_data.copy()


    lat = df[lat_field]
    lon = df[lon_field]


    gdf = gp.GeoDataFrame(df, geometry=gp.points_from_xy(lon, lat))
    gdf_length = len(gdf.index)

    labels = [""] * gdf_length

    for i in range(0, shp_length):
        shp_label = shp.iloc[i][label]
        shp_geometry = shp.iloc[i][geometry]

        mask = gdf.within(shp_geometry)
        for i in range(0, gdf_length):
            if mask[i]:
                if len(labels[i]) == 0:
                    labels[i] = shp_label
                else:
                    labels[i] = labels[i] + "," + shp_label


    output_data["regions"] = labels


    #write the output records in the first output
    if output_data is not None:
        omniscope_api.write_output_records(output_data, output_number=0)
    omniscope_api.close()