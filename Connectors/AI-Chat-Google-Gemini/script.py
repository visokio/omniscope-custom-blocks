import pandas as pd
from omniscope.api import OmniscopeApi
from google import genai
from google.genai import types

omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

API_Key = omniscope_api.get_option("GEMINI_API_KEY")
prompt = omniscope_api.get_option("Prompt")
systemPrompt = omniscope_api.get_option("SystemPrompt")
model = omniscope_api.get_option("Model")
temperature = omniscope_api.get_option("Temperature")

client = genai.Client(api_key=API_Key)

result_df = []
for index, row in input_data.iterrows():
    the_prompt = row[prompt]
    the_systemprompt = row[systemPrompt]
    
    message = client.models.generate_content(
        model=model,
        contents=the_prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=the_systemprompt
           ) 
        )

    result_df.append({"Prompt" : the_prompt, "System Prompt": the_systemprompt, "Response" : message.text})
    
output_data = pd.DataFrame(result_df)


#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()