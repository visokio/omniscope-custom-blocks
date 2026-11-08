"""AI Chat - Claude

Sends one prompt per record to Anthropic's Messages API (Claude) and adds the reply to the record.
Options are described in the block's README. Records with an empty prompt are passed through with an empty
response and are not sent. Any failed request stops the block with the service's error message.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from omniscope.api import OmniscopeApi

omniscope_api = OmniscopeApi()

# ---------------------------------------------------------------------------------------------- helpers

def is_blank(value):
    """True for a missing value, NaN or text that is only spaces."""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def as_text(value):
    """A field value as prompt text: whole numbers without ".0", dates as ISO text, None for blanks."""
    if is_blank(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def output_names(columns):
    """The names of the two added fields: Response and Truncated, numbered if the input already has them."""
    taken = {str(c) for c in columns}
    n = 1
    while True:
        suffix = "" if n == 1 else f" {n}"
        names = (f"Response{suffix}", f"Truncated{suffix}")
        if not (set(names) & taken):
            return names
        n += 1


def failure_message(record, exc):
    """A short message for a failed request, with a hint for the common causes."""
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    detail = " ".join(str(exc).split())[:400]
    hint = {
        401: " Check the API key.",
        403: " Check the API key and that it may use this model.",
        404: " Check the model name.",
        429: " The service's rate or spending limit was reached: lower Requests at a time, or try again later.",
    }.get(status if isinstance(status, int) else None, "")
    return f"The request for record {record} failed ({type(exc).__name__}): {detail}{hint}"


# -------------------------------------------------------------------------------------- check options

input_data = omniscope_api.read_input_records(input_number=0)
if input_data is None:
    omniscope_api.abort("Connect the records to send to the block's input.")

api_key = omniscope_api.get_option("AnthropicApiKey")
model = (omniscope_api.get_option("Model") or "").strip()
if is_blank(api_key):
    omniscope_api.abort("Enter your Anthropic API key.")

prompt_field = omniscope_api.get_option("Prompt")
system_field = omniscope_api.get_option("SystemPrompt")
max_tokens = omniscope_api.get_option("MaxTokens")
concurrency = omniscope_api.get_option("Concurrency")

if not model:
    omniscope_api.abort("Enter a model name.")
if not prompt_field:
    omniscope_api.abort("Choose the field that holds the prompt (User prompt field).")
for label, field in (("User prompt field", prompt_field), ("System prompt field", system_field)):
    if field and field not in input_data.columns:
        omniscope_api.abort(f"{label}: the input has no field called '{field}'.")
if max_tokens is not None and max_tokens < 1:
    omniscope_api.abort("Maximum response length must be at least 1 token.")
concurrency = min(max(int(concurrency or 1), 1), 16)

# ------------------------------------------------------------------------------------------ requests

def make_client():
    import anthropic
    return anthropic.Anthropic(api_key=api_key, max_retries=5)


def ask(client, prompt, system):
    """One Messages request. Returns (reply text, whether it stopped at the length limit)."""
    request = {"model": model, "max_tokens": int(max_tokens or 1024),
               "messages": [{"role": "user", "content": prompt}]}
    if system:
        request["system"] = system
    message = client.messages.create(**request)
    text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
    return text, message.stop_reason == "max_tokens"


# ------------------------------------------------------------------------------------------ send

prompts = [as_text(v) for v in input_data[prompt_field]]
systems = [as_text(v) for v in input_data[system_field]] if system_field else [None] * len(prompts)
to_send = [i for i, p in enumerate(prompts) if p is not None]

results = [None] * len(prompts)
failure = None
if to_send:
    client = make_client()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(ask, client, prompts[i], systems[i]): i for i in to_send}
        for done, future in enumerate(as_completed(futures), 1):
            i = futures[future]
            try:
                results[i] = future.result()
            except Exception as exc:  # noqa: BLE001 - any SDK or network error stops the block
                failure = failure_message(i + 1, exc)
                pool.shutdown(wait=False, cancel_futures=True)
                break
            if done % 25 == 0:
                omniscope_api.update_message(f"Received {done} of {len(to_send)} responses")
if failure:
    omniscope_api.abort(failure)

# ---------------------------------------------------------------------------------------- output

response_name, truncated_name = output_names(input_data.columns)
output_data = input_data.copy()
output_data[response_name] = pd.Series([r[0] if r else None for r in results], index=input_data.index, dtype=object)
output_data[truncated_name] = pd.array([r[1] if r else None for r in results], dtype="boolean")
omniscope_api.write_output_records(output_data, output_number=0)

skipped = len(prompts) - len(to_send)
truncated = sum(1 for r in results if r and r[1])
summary = f"{len(to_send)} {'response' if len(to_send) == 1 else 'responses'} received"
if skipped:
    summary += f"; {skipped} {'record' if skipped == 1 else 'records'} with an empty prompt not sent"
if truncated:
    summary += f"; {truncated} {'response' if truncated == 1 else 'responses'} cut short at the maximum length"
omniscope_api.close(summary + ".")
