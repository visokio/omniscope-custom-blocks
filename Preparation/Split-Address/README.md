# Split Address

Splits a street address such as "Kerkstraat 12A" or "221B Baker Street" into the street name, the house number and a suffix (the letter or addition after the number).

Delivery and customer files often keep the street and house number in one field, while a mailing system, a geocoding service or a check against a reference list wants them apart. This block adds three fields: the **street name**, the **house number** (digits only) and the **suffix** (whatever follows the number: a letter, `bis`, `II`, `Apt B`).

**The field must hold the street and number only.** Towns, postcodes and countries belong in fields of their own; flats and buildings named before the number are not handled (see the table below).

## What it handles

The block tries a fixed list of patterns, street first or number first, with or without a comma. These results are checked by the block's tests:

| Address | Street name | Number | Suffix |
|---|---|---|---|
| Kerkstraat 12A | Kerkstraat | 12 | A |
| Baker Street 221-B | Baker Street | 221 | B |
| Baker Street, 221 B | Baker Street | 221 | B |
| Baker Street 221 Apt B | Baker Street | 221 | Apt B |
| Molenweg 7 bis | Molenweg | 7 | bis |
| Kerkstraat 12-II | Kerkstraat | 12 | II |
| Bredgade 40, 2. tv | Bredgade | 40 | 2. tv |
| 221B Baker Street | Baker Street | 221 | B |
| 221 Apt B, Baker Street | Baker Street | 221 | Apt B |
| 14 Mill Lane | Mill Lane | 14 | |
| 8, rue des Lilas | rue des Lilas | 8 | |
| 1600 Pennsylvania Avenue NW | Pennsylvania Avenue NW | 1600 | |
| Hauptstraße 5 | Hauptstraße | 5 | |
| Straße des 17. Juni 135 | Straße des 17. Juni | 135 | |
| Avenida 5 de Mayo 22 | Avenida 5 de Mayo | 22 | |
| Station Road | Station Road | | |

Street names can be in any alphabet. Spaces and commas around the address are ignored.

## What it gets wrong

These formats give a wrong or empty result. Check the output if your addresses look like them.

| Address | Street name | Number | Suffix | What went wrong |
|---|---|---|---|---|
| Flat 3, 12 High Street | Flat | 3 | 12 High Street | A flat or unit before the number is taken as the street |
| Unit 5 Riverside Park | Unit | 5 | Riverside Park | The same |
| Baker Street 221B, London | Baker Street | 221 | B, London | A town after the number ends up in the suffix |
| 221 Baker Street, London NW1 6XE | Baker Street, London NW1 6XE | 221 | | A town and postcode after the street end up in the street name |
| 12-14 Market Place | | | | Number ranges are not recognised |
| Laan 1940-1945 10 | Laan | 1940 | 1945 10 | A street name ending in numbers is cut at the first number |
| PO Box 123 | PO Box | 123 | | A PO box is split like a street |

An address that fits no pattern gets **empty** street name, number and suffix fields, and the block's message says how many there were ("1 of 15 addresses not recognised"). Filter on an empty street name to find them.

## Language and libraries

Python. It uses pandas (BSD 3-Clause licence), part of Omniscope's Python environment, and `re` from the Python standard library. It needs nothing else installed.

## Inputs
- **Input 1**: records with a text field holding a street address.

## Options

| Group | Option | Name in script | Type | Description |
|---|---|---|---|---|
| | Address field | `address` | Field (text) | The text field holding the street address. From input 1. |
| New field names | Street name field | `streetname` | Text | Name of the new field for the street name. Default `Streetname`. |
| New field names | House number field | `streetnumber` | Text | Name of the new field for the house number. Default `Streetnumber`. |
| New field names | Suffix field | `suffix` | Text | Name of the new field for what follows the number. Default `Suffix`. |

A blank name gives the default. The three names must differ; a name already used by an input field replaces that field.

## Outputs
- **Split** (`Output Data`): the input records with the three new fields. The house number is text (digits only); missing parts are empty.

## Size of input

Each distinct address is split once. In tests, 200,000 records took under a second.

## Source
[script.py](script.py)

The sample data in `sample-data/` is invented for the demo.
