import pandas as pd
from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

# read the records associated to the first block input
input_data = omniscope_api.read_input_records(input_number=0)

API_Key = omniscope_api.get_option("OpenAiApiKey")
prompt = omniscope_api.get_option("Prompt")
systemPrompt = omniscope_api.get_option("SystemPrompt")
model = omniscope_api.get_option("Model")

from openai import OpenAI
client = OpenAI(api_key=API_Key)

result_df = []
for index, row in input_data.iterrows():
    the_prompt = row[prompt]
    the_systemprompt = row[systemPrompt]

    response = client.chat.completions.create(
      model=model,
      messages=[
        {"role": "system", "content": the_systemprompt},
        {
          "role": "user",
          "content": the_prompt
        }
      ],
      temperature=1,
      max_tokens=256,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0 
    )
    
    result_df.append({"Prompt" : the_prompt, "System Prompt": the_systemprompt, "Response" : response.choices[0].message.content})
    
output_data = pd.DataFrame(result_df) 

#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()
