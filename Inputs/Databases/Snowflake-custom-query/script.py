import pandas as pd
from omniscope.api import OmniscopeApi
import snowflake.connector

# Initialize Omniscope API
omniscope_api = OmniscopeApi()

# Retrieve options from the block configuration
account = omniscope_api.get_option('account')
user = omniscope_api.get_option('user')
password = omniscope_api.get_option('password')
warehouse = omniscope_api.get_option('warehouse')
database = omniscope_api.get_option('database')
custom_sql = omniscope_api.get_option('custom_sql')

# Establish a connection to Snowflake
def connect_to_snowflake():
    return snowflake.connector.connect(
        user=user,
        password=password,
        account=account,
        warehouse=warehouse,
        database=database
    )

# Fetch data using the SQL query
def fetch_data_from_snowflake(sql_query):
    try:
        # Connect to Snowflake
        conn = connect_to_snowflake()
        
        # Execute the query and fetch data into a DataFrame
        df = pd.read_sql(sql_query, conn)
        
        # Close the connection
        conn.close()
        
        return df
    except Exception as e:
        omniscope_api.error(f"Error executing SQL query: {str(e)}")
        return pd.DataFrame()  # Return an empty dataframe on error


# Fetch the data
output_data = fetch_data_from_snowflake(custom_sql)

# Write the output records to the first output if there is data
if output_data is not None and not output_data.empty:
    omniscope_api.write_output_records(output_data, output_number=0)

# Close the API after processing is complete
omniscope_api.close()