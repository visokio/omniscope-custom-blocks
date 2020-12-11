# Split Address

Splits an address field into streetname, streetnumber, and suffix.

An address is not expected to contain zip codes, city names or country names.
Some examples of valid input patterns:

- Baker Street 221B
- Baker Street 221 B
- Baker Street 221-B
- Baker Street, 221 B
- Baker Street 221 Apt B
- 221B, Baker Street
- 221 B, Baker Street
- 221 Apt B, Baker Street
- 221 Baker Street

## Language
Python

## Parameters
### Address
Adjust to the name of the field which contains the addresses.

### Streetname
Name of the output field containing the streetname.

### Streetnumber
Name of the output field containing the streetnumber.

### Suffix
Name of the output field containing the suffix.

## Dependencies
re

## Source
[script.py](https://github.com/visokio/omniscope-custom-blocks/blob/master/Preparation/Split%20Address/script.py)
