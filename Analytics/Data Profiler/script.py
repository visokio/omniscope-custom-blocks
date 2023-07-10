import pandas as pd
import numpy as np
from scipy import stats
from omniscope.api import OmniscopeApi

# Initialise the API
api = OmniscopeApi()

# Read input records
input_data = api.read_input_records()

# Generate a basic statistics summary
description = input_data.describe(include='all').transpose()

# Add null counts to the description
description['null_count'] = input_data.isnull().sum()

# Determine the skewness of numeric columns
numeric_columns = input_data.select_dtypes(include=np.number).columns
description.loc[numeric_columns, 'skewness'] = input_data[numeric_columns].skew()

# Create a DataFrame to hold the results
results = pd.DataFrame()

# Determine the type, statistics, null values, and potential anomalies for each field
for column in input_data.columns:
    dtype = str(input_data[column].dtype)
    column_stats = description.loc[column].to_dict()
    
    # Prepare the results row
    row_df = pd.DataFrame([{"Field": column, "Type": dtype, **column_stats}])
    
    # Append the results to the DataFrame
    results = pd.concat([results, row_df], ignore_index=True)

    # If the column is numeric, calculate the z-scores
    if pd.api.types.is_numeric_dtype(input_data[column]):
        cleaned_series = input_data[column].dropna().astype('float64') # ensure all data are float64 for compatibility
        z_scores = stats.zscore(cleaned_series)
        
        # Create new columns in the input_data dataframe for the z-score, anomaly status and likelihood
        input_data[column + '_z_score'] = np.nan
        input_data[column + '_anomaly'] = np.nan
        input_data[column + '_likelihood'] = np.nan
        input_data.loc[cleaned_series.index, column + '_z_score'] = z_scores
        input_data.loc[cleaned_series.index, column + '_anomaly'] = (np.abs(z_scores) > 3).astype(int)
        input_data.loc[cleaned_series.index, column + '_likelihood'] = 1 - stats.norm.sf(np.abs(z_scores))  # using sf (survival function) to get one-tailed p-value

# Reorder columns so that the new z_score, anomaly and likelihood columns appear at the end
input_data = input_data[[col for col in input_data if not col.endswith(('_z_score', '_anomaly', '_likelihood'))] 
            + [col for col in input_data if col.endswith('_z_score')] 
            + [col for col in input_data if col.endswith('_anomaly')]
            + [col for col in input_data if col.endswith('_likelihood')]]

# Write the analysis to the first output
api.write_output_records(results)

# Write the input data (now with added z-scores, anomaly status and likelihood) to the second output
api.write_output_records(input_data, output_number=1)

api.commit('Data analysis complete.')