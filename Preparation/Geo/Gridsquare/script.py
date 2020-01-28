from omniscope.api import OmniscopeApi
import pandas


# Derived from https://ham.stackexchange.com/questions/6462/how-can-one-convert-from-grid-square-to-lat-long
def GetLon(ONE, THREE, FIVE):
    Field = ((ord(ONE.lower()) - 97) * 20) 
    Square = int(THREE) * 2
    SubSquareLow = (ord(FIVE.lower()) - 97) * (2/24)
    SubSquareHigh = SubSquareLow + (2/24)

    StartLon = Field + Square + SubSquareLow - 180
    EndLon = Field + Square + SubSquareHigh - 180

    return StartLon, EndLon

def GetLat(TWO, FOUR, SIX):
    Field = ((ord(TWO.lower()) - 97) * 10) 
    Square = int(FOUR)
    SubSquareLow = (ord(SIX.lower()) - 97) * (1/24)
    SubSquareHigh = SubSquareLow + (1/24)

    StartLat = Field + Square + SubSquareLow - 90
    EndLat = Field + Square + SubSquareHigh - 90    

    return StartLat, EndLat

def convert(strMaidenHead, lons, lats):
    ONE = strMaidenHead[0:1]
    TWO = strMaidenHead[1:2]
    THREE = strMaidenHead[2:3]
    FOUR = strMaidenHead[3:4]
    FIVE = strMaidenHead[4:5]
    SIX = strMaidenHead[5:6]
    
    (startLon, endLon) = GetLon(ONE, THREE, FIVE)
    (startLat, endLat) = GetLat(TWO, FOUR, SIX)
    
    lon = (startLon + endLon) / 2
    lat = (startLat + endLat) / 2
    
    lons.append(lon)
    lats.append(lat)


omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

# read the value of the option called "my_option"
gs_field = omniscope_api.get_option("gsfield")
lon_field = omniscope_api.get_option("lonfield")
lat_field = omniscope_api.get_option("latfield")

codes = input_data[gs_field]

lons = []
lats = []

for k in codes:
    convert(k, lons, lats)

output_data = input_data

output_data = pandas.concat([
  output_data, 
  pandas.DataFrame(lons, columns=[lon_field])
], axis=1)

output_data = pandas.concat([
  output_data, 
  pandas.DataFrame(lats, columns=[lat_field])
], axis=1)



#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()