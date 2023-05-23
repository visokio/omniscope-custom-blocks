from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

import pandas as pd
from flipside import Flipside
from flipside.errors import ApiError, QueryRunExecutionError, QueryRunRateLimitError, QueryRunTimeoutError, ServerError

# Initialize `Flipside` with your API Key
sdk = Flipside(omniscope_api.get_option("key"))

# SQL query
sql = f"""{omniscope_api.get_option("query").strip()}"""
print(sql)

# Initialize an empty DataFrame to store all results
all_data = None

# Try to execute the query
try:
    page_number = 1
   
    omniscope_api.update_message(f'Submitting query...')
    
    query_result_set = sdk.query(
      sql,
      max_age_minutes=0,
      timeout_minutes=20,
      retry_interval_seconds=1,
      page_size=100,
      page_number=page_number
    )
    
    while True:
        
        omniscope_api.update_message(f'Submitted query... retrieving records (page {page_number})')

        # Convert the results to a pandas DataFrame
        page_results = sdk.get_query_results(
            query_result_set.query_id,
            page_number=page_number,
            page_size=100
        )
                
        df = pd.DataFrame(page_results.records)
	
        # If the DataFrame is empty, break the loop
        if df is None or df.empty:
            break

        # Append the data to the all_data DataFrame
        if (all_data is None): 
            all_data = df
        else:
            all_data = pd.concat([all_data, df], ignore_index=True)

        # Increment the page number
        page_number += 1

    output_data = all_data
    #write the output records in the first output
    if output_data is not None:
        omniscope_api.write_output_records(output_data, output_number=0)
        
except QueryRunRateLimitError as e:
    omniscope_api.abort(f"You have been rate limited: {e.message}")
except QueryRunTimeoutError as e:
    omniscope_api.abort(f"Your query has taken longer than the specified timeout to run: {e.message}")
except QueryRunExecutionError as e:
    omniscope_api.abort(f"Your SQL query is malformed: {e.message}")
except ServerError as e:
    omniscope_api.abort(f"A server-side error has occurred: {e.message}")
except ApiError as e:
    omniscope_api.abort(f"An API error has occurred: {e.message}")


omniscope_api.close()