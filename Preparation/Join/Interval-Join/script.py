from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()
from pandasql import sqldf
import pandas as pd

# read the records associated to the first block input
left = omniscope_api.read_input_records(input_number=0)
right = omniscope_api.read_input_records(input_number=1)

# read the value of the option called "my_option"
# my_option = omniscope_api.get_option("my_option")

value_field = omniscope_api.get_option("value")
start_field = omniscope_api.get_option("start")
start_comparator = omniscope_api.get_option("start_comparator")
end_field = omniscope_api.get_option("end")
end_comparator = omniscope_api.get_option("end_comparator")
join_type = omniscope_api.get_option("join_type")

left_eq_field = omniscope_api.get_option("left")
right_eq_field = omniscope_api.get_option("right")

if left is None:
    omniscope_api.abort("missing first input")

if right is None:
    omniscope_api.abort("missing right input")
    
q = f"""
    SELECT A.*, B.*
        FROM
        left A
        {join_type} JOIN
        right B
        ON
        A."{value_field}" {start_comparator} B."{start_field}" AND
        A."{value_field}" {end_comparator} B."{end_field}"
"""

if left_eq_field is not None and right_eq_field is not None:
    q = q + f""" AND A."{left_eq_field}" = B."{right_eq_field}";"""
else:
    q = q + ";"
    
df = sqldf(q, globals())

def dedup_names(names):
    names = list(names)
    counts = {}

    for i, col in enumerate(names):
        cur_count = counts.get(col, 0)

        if cur_count > 0:
            names[i] = '%s.%d' % (col, cur_count)

        counts[col] = cur_count + 1

    return names
        

while sum(df.columns.duplicated(keep=False)) > 0:        
    df.columns=dedup_names(df.columns)


output_data = df


#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()