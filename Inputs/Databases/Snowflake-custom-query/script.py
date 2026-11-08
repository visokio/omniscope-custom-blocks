"""Snowflake Custom Query: runs a SQL query on Snowflake and outputs the result."""
import datetime
import decimal
import math
import os

import pandas as pd
import snowflake.connector
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()


def text_option(name):
    value = omniscope_api.get_option(name)
    return value.strip() if isinstance(value, str) else ""


account = text_option("account")
user = text_option("user")
password = omniscope_api.get_option("password") or ""
private_key_file = text_option("private_key_file")
private_key_password = omniscope_api.get_option("private_key_password") or ""
warehouse = text_option("warehouse")
database = text_option("database")
schema = text_option("schema")
role = text_option("role")
custom_sql = text_option("custom_sql")

if not account or not user:
    omniscope_api.abort("Enter the Snowflake account identifier and the user name.")
if not password and not private_key_file:
    omniscope_api.abort("Enter a password, or the path of a private key file for key-pair authentication.")
if private_key_file and not os.path.isfile(private_key_file):
    omniscope_api.abort(f"The private key file {private_key_file!r} was not found on the server.")
if not custom_sql:
    omniscope_api.abort("Enter the SQL query to run.")

params = {"account": account, "user": user, "application": "Omniscope"}
if private_key_file:
    params["private_key_file"] = private_key_file
    if private_key_password:
        params["private_key_file_pwd"] = private_key_password
else:
    params["password"] = password
for key, value in (("warehouse", warehouse), ("database", database), ("schema", schema), ("role", role)):
    if value:
        params[key] = value


def missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def to_omniscope(df):
    """NUMBER with decimals arrives as Python Decimal: make it a decimal number. TIMESTAMP_TZ / _LTZ values carry
    their own offsets: make them one UTC date field. TIME becomes text."""
    for col in df.columns:
        s = df[col]
        if isinstance(s.dtype, pd.DatetimeTZDtype):
            df[col] = s.dt.tz_convert("UTC")
            continue
        if s.dtype != object:
            continue
        present = s[~s.map(missing)]
        if not len(present):
            continue
        if present.map(lambda v: isinstance(v, decimal.Decimal)).all():
            s = s.map(lambda v: math.nan if missing(v) else float(v)).astype("float64")
        elif present.map(lambda v: isinstance(v, datetime.datetime)).all():
            s = pd.to_datetime(s, utc=any(v.tzinfo is not None for v in present))
        elif present.map(lambda v: isinstance(v, datetime.date)).all():
            s = pd.to_datetime(s)
        elif present.map(lambda v: isinstance(v, datetime.time)).all():
            s = s.map(lambda v: None if missing(v) else v.isoformat())
        elif present.map(lambda v: isinstance(v, (bytes, bytearray))).any():
            s = s.map(lambda v: v.hex() if isinstance(v, (bytes, bytearray)) else v)
        df[col] = s
    return df


try:
    conn = snowflake.connector.connect(**params)
except Exception as exc:
    omniscope_api.abort(f"Could not connect to Snowflake: {exc}")

try:
    cursor = conn.cursor()
    omniscope_api.update_message("Running the query")
    cursor.execute(custom_sql)
    if cursor.description is None:
        output_data = None
    else:
        names, seen = [], set()
        for d in cursor.description:  # SELECT a.id, b.id gives two ID columns: the second becomes ID_2
            name, n = d[0], 1
            while name.lower() in seen:
                n += 1
                name = f"{d[0]}_{n}"
            seen.add(name.lower())
            names.append(name)
        output_data = pd.DataFrame.from_records(cursor.fetchall(), columns=names)
except Exception as exc:
    omniscope_api.abort(f"Error running the query: {exc}")
finally:
    conn.close()

if output_data is None:
    omniscope_api.close("The statement ran but returned no table")
else:
    output_data = to_omniscope(output_data)
    omniscope_api.write_output_records(output_data, output_number=0)
    omniscope_api.close(f"{len(output_data)} records")
