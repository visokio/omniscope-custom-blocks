from omniscope.api import OmniscopeApi
omniscope_api = OmniscopeApi()

import pandas as pd
import requests
from tabulate import tabulate
import json

# Example DataFrame
df = omniscope_api.read_input_records(input_number=0)

# Configuration
text_format = omniscope_api.get_option("text_format")
bot_token = omniscope_api.get_option("bot_token")
chat_id = omniscope_api.get_option("chat_id")

# Convert DataFrame based on format
if text_format == "JSON":
    message_text = df.to_json(orient="records", indent=2)
elif text_format == "TABLE":
    message_text = tabulate(df, headers='keys', tablefmt='grid', showindex=False)
elif text_format == "CONCAT":
    message_text = ' '.join(df.astype(str).agg(' '.join, axis=1))
else:
    raise ValueError("Invalid text_format. Choose from 'JSON', 'TABLE', or 'CONCAT'.")

# Send to Telegram
url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
payload = {
    "chat_id": chat_id,
    "text": message_text
}
response = requests.post(url, json=payload)

response_data = {
    "status_code": [response.status_code],
    "ok": [response.ok],
    "reason": [response.reason],
    "response_json": [json.dumps(response.json(), indent=2) if response.headers.get("Content-Type", "").startswith("application/json") else response.text]
}

output_data = pd.DataFrame(response_data)


#write the output records in the first output
if output_data is not None:
    omniscope_api.write_output_records(output_data, output_number=0)
omniscope_api.close()