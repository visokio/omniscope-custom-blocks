import pandas as pd
from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()
input_1 = omniscope_api.read_input_records(input_number=0)
import numpy as np

# Define a function to anonymize text fields in a DataFrame
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
    unique_values = set()  # Use a set to avoid duplicates
    for col in selectedFields:
        if col in df.columns and df[col].dtype == 'object':  # Check if the column exists and is of type object (text)
            unique_values.update(df[col].unique())  # Add unique values to the set
    
    # Generate unique words based on the number of unique values
    num_unique_values = len(unique_values)
    words = [f"{base_words[i % len(base_words)]}{(i // len(base_words)) + 1}" for i in range(num_unique_values)]
    
    # Create a mapping for each unique value to a word
    for value in unique_values:
        mapping[value] = words.pop(0)  # Get the next unique word from the list
    
    # Replace the original values with their mapped words in the selected columns
    for col in selectedFields:
        if col in df.columns and df[col].dtype == 'object':  # Check if the column exists and is of type object (text)
            df[col] = df[col].map(mapping)


selectedFields = omniscope_api.get_option("selectedFields")
print(selectedFields)
if (selectedFields == None or not selectedFields):
   selectedFields = input_1.columns;
# Call the function with the input DataFrame
anonymize_text_fields(input_1, selectedFields)
output = input_1.copy()

omniscope_api.write_output_records(output, output_number=0)
omniscope_api.close()