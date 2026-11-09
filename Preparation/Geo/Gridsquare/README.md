# Gridsquare

Converts Maidenhead grid square locators (such as IO91wm) to the longitude and latitude of the square's centre.

The [Maidenhead Locator System](https://en.wikipedia.org/wiki/Maidenhead_Locator_System) names a rectangle of the earth's surface with a short code of letters and digits in pairs. It is the usual way to give a station's location in amateur radio, and is used in some field and sensor logs. Each pair narrows the square down:

| Characters | Example | Square size | Roughly, at the latitude of London |
|---|---|---|---|
| 2 (field) | `IO` | 20 x 10 degrees | |
| 4 (square) | `IO91` | 2 x 1 degrees | 139 x 111 km |
| 6 (subsquare) | `IO91wm` | 5 x 2.5 minutes | 6 x 5 km |
| 8 (extended square) | `IO91wm52` | 30 x 15 seconds | 570 x 460 m |
| 10 | `IO91wm52kx` | 1.25 x 0.625 seconds | 24 x 19 m |

The block adds two Decimal fields with the longitude and latitude of the **centre** of the square, in degrees (WGS 84), so the records can be mapped or measured. The longer the locator, the more precise the point.

Things to know:

- Locators of 2, 4, 6, 8 or 10 characters are read, in upper or lower case, with spaces around them ignored.
- A value that is not a valid locator (wrong length, a letter out of range such as `IO92ZZ`, where the subsquare letters only go to X) gets empty coordinates, as does an empty value. The block's message says how many records were located and how many were not valid.
- If the input already has a field with one of the new names, it is replaced, in its place.

## Language and libraries

Python, using pandas (BSD 3-Clause), part of Omniscope's Python environment. Nothing else to install.

## Inputs
- **Input 1**: records with a text field of grid square locators.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Grid square field | `gsfield` | Field | The text field with the locators, for example "IO91wm". From input 1. |
| Longitude field | `lonfield` | Text | Name of the field to create for the longitude (X) of the square's centre. Default: Longitude. |
| Latitude field | `latfield` | Text | Name of the field to create for the latitude (Y) of the square's centre. Default: Latitude. |

## Outputs
- **Located** (`Output Data`): the input records, in their order, with the longitude and latitude fields added (Decimal, degrees); empty where the locator is missing or not valid.

## Size of input

210,000 records took under a second in tests.

## Source
[script.py](script.py)

The calculation follows the published definition of the Maidenhead system; the results were checked against an independent implementation for every precision.

The sample data in `sample-data/station-log.csv` is invented (station names and contact counts are made up).
