import pandas as pd
from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()
input_1 = omniscope_api.read_input_records(input_number=0)
from diffprivlib.mechanisms import Laplace
import numpy as np

# Function to anonymize text fields in a DataFrame
def anonymize_text_fields(df, selectedFields):
    # A base list of recognizable English words with at least 4 characters
    base_words = [
        "apple", "banana", "cherry", "grape", "honeydew", "kiwi", "lemon", "mango", 
        "nectarine", "orange", "papaya", "quince", "raspberry", "strawberry", 
        "tangerine", "vanilla", "watermelon", "zucchini", "abandon", "ability", 
        "accept", "account", "achieve", "activity", "actually", "addition", 
        "address", "adventure", "agreement", "alternative", "analysis", "analyze", 
        "appearance", "application", "appropriate", "argument", "arrangement", 
        "association", "assumption", "attraction", "authority", "available", 
        "beautiful", "behavior", "believe", "beneficial", "billion", "business", 
        "calendar", "capability", "celebration", "challenge", "character", 
        "children", "circular", "citizens", "clarity", "collection", 
        "comfortable", "community", "competition", "complaint", "conclusion", 
        "condition", "conference", "connection", "consideration", "construction", 
        "consultation", "consumer", "conversation", "corporation", "creative", 
        "critical", "customer", "database", "decision", "definition", "democracy", 
        "development", "difference", "discussion", "education", "effective", 
        "emergency", "emotional", "encouragement", "environment", "essential", 
        "evaluation", "experience", "explanation", "exploration", "expression", 
        "fascinate", "favorable", "financial", "foundation", "freedom", 
        "friendship", "generally", "government", "guidance", "happiness", 
        "historical", "immediate", "important", "impressive", "influence", 
        "information", "inspiration", "interaction", "interesting", "introduction", 
        "investigation", "knowledge", "leadership", "legislation", "literature", 
        "management", "motivation", "observation", "opportunity", "organization", 
        "participation", "performance", "perspective", "political", "population", 
        "presentation", "professional", "protection", "publication", 
        "relationship", "representation", "responsibility", "satisfaction", 
        "scientific", "significant", "situation", "sophisticated", "strategic", 
        "successful", "technology", "treatment", "understanding", "volunteer", 
        "wonderful", "workplace"
    ]
    
    # Create a mapping dictionary to store original values and their anonymized counterparts
    mapping = {}
    
    # Collect unique values across all selected text fields
    unique_values = set()
    for col in selectedFields:
        if col in df.columns and df[col].dtype == 'object':  # Only process text fields
            unique_values.update(df[col].unique())
    
    # Generate unique words based on the number of unique values
    num_unique_values = len(unique_values)
    words = [f"{base_words[i % len(base_words)]}{(i // len(base_words)) + 1}" for i in range(num_unique_values)]
    
    # Map each unique text value to a generated word
    for value in unique_values:
        mapping[value] = words.pop(0)
    
    # Replace original text values with the mapped words
    for col in selectedFields:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].map(mapping)

# Anonymise numeric fields using the Laplace mechanism
def anonymize_numeric_fields(df, selectedFields, epsilon=1.0, sensitivity=1.0):
    for col in selectedFields:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            mech = Laplace(epsilon=epsilon, sensitivity=sensitivity)
            # Apply Laplace noise to each value in the column
            df[col] = df[col].apply(lambda x: mech.randomise(x))

# Anonymise datetime fields using the Laplace mechanism
def anonymize_date_fields(df, selectedFields, epsilon=1.0, sensitivity=86400):
    for col in selectedFields:
        if col in df.columns and pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], errors='coerce')
            mech = Laplace(epsilon=epsilon, sensitivity=sensitivity)
            def add_noise(dt):
                if pd.isnull(dt):
                    return pd.NaT
                ts = dt.timestamp()
                noisy_ts = mech.randomise(ts)
                noisy_dt = pd.to_datetime(noisy_ts, unit='s', errors='coerce')
                # Convert to Python datetime and drop microseconds.
                return noisy_dt.to_pydatetime().replace(microsecond=0) if pd.notnull(noisy_dt) else pd.NaT
            df[col] = df[col].apply(add_noise)


# For numeric fields: more conservative defaults.
epsilon_numeric = omniscope_api.get_option("epsilon_numeric")
if epsilon_numeric is None:
    epsilon_numeric = 5.0
else:
    epsilon_numeric = float(epsilon_numeric)
sensitivity_numeric = omniscope_api.get_option("sensitivity_numeric")
if sensitivity_numeric is None:
    sensitivity_numeric = 10.0
else:
    sensitivity_numeric = float(sensitivity_numeric)

# For datetime fields: more conservative defaults.
epsilon_date = omniscope_api.get_option("epsilon_date")
if epsilon_date is None:
    epsilon_date = 5.0
else:
    epsilon_date = float(epsilon_date)
sensitivity_date = omniscope_api.get_option("sensitivity_date")
if sensitivity_date is None:
    sensitivity_date = 3600  # one hour in seconds
else:
    sensitivity_date = float(sensitivity_date)


# Retrieve the selected fields option, or use all columns if not provided
selectedFields = omniscope_api.get_option("selectedFields")
print(selectedFields)
if selectedFields is None or not selectedFields:
   selectedFields = input_1.columns

# Apply anonymization functions to the input DataFrame
anonymize_text_fields(input_1, selectedFields)
anonymize_numeric_fields(input_1, selectedFields)
anonymize_date_fields(input_1, selectedFields)

output = input_1.copy()

omniscope_api.write_output_records(output, output_number=0)
omniscope_api.close()