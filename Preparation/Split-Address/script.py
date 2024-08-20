from omniscope.api import OmniscopeApi
import pandas as pd
import re


def f(s):
    """Splits address into streetname and rest"""
    match = re.search(r"^(.+[a-zA-Z]{2,}),\s*(\d+.*)$", s)
    if match:
        return match.group(1), match.group(2)
    
    match = re.search(r"^(\d+.*),\s*(\D+)$", s)
    if match:
        return match.group(2), match.group(1)
        
    match = re.search(r"^(.+[a-zA-Z]{2,})[\s,\.\-]+(\d+.*)$", s)
    if match:
        return match.group(1), match.group(2)
        
    match = re.search(r"^[^\d@]+$", s)
    if match:
        return match.group(), ''
        
    match = re.search(r"^([a-zA-Z\s\.']+)(\d+.*)$", s)
    if match:
        return match.group(1), match.group(2)
        
    match = re.search(r"^(\d+[a-zA-Z]*),\s*(.*)$", s)
    if match:
        return match.group(2), match.group(1)
        
    match = re.search(r"^(\d+)\s+(.*[a-zA-Z])$", s)
    if match:
        return match.group(2), match.group(1)
        
    return '', ''

def g(s):
    """Splits the rest into streetnumber and suffix"""
    match = re.search(r"^(\d+)[\s\-./,]*(.*)$", s)
    if match:
        return match.group(1), match.group(2)
        
    return '', ''


omniscope_api = OmniscopeApi()

ADDRESS = omniscope_api.get_option("address")
STREETNAME = omniscope_api.get_option("streetname") or "Streetname"
STREETNUMBER = omniscope_api.get_option("streetnumber") or "Streetnumber"
SUFFIX = omniscope_api.get_option("suffix") or "Suffix"


df = omniscope_api.read_input_records(input_number=0)
address = df[ADDRESS].astype(str).apply(lambda s: s.strip(','))

df[STREETNAME], rest = zip(*address.map(f))
df[STREETNUMBER], df[SUFFIX] = zip(*pd.Series(rest).map(g))

omniscope_api.write_output_records(df, output_number=0)
omniscope_api.close()