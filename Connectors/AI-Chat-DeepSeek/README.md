# AI Chat - DeepSeek

Sends the prompt in each record to a DeepSeek model and adds the reply to the record.

Sorting free-text descriptions into categories is a common job for a language model. This block does it inside a workflow with your own DeepSeek API key: nothing needs setting up in the server's AI settings, and every request is billed to that key's account.

- Choose the **User prompt field**: the text each record sends. An optional **System prompt field** carries the instructions (the model's role, the categories to choose from, the answer format); it is usually the same text on every record, made with a Formula block.
- The output is the input with two fields added: **Response**, the model's reply, and **Truncated**, true when the reply stopped at the maximum response length. If the input already has a Response field, the new ones are called Response 2 and Truncated 2.
- Records with an empty prompt are passed through with both fields empty and are not sent. Numbers and dates in the prompt field are sent as text.
- Requests can go several at a time (**Requests at a time**, 4 by default); the output keeps the input's order.
- If a request fails, the block stops with the service's message, the record number and a hint (for example "Check the API key"); there is no partial output.

The default model is `deepseek-flash` (checked against DeepSeek's API documentation on 6 November 2026: the previous default, deepseek-chat, was one of the two legacy model names DeepSeek discontinued on 24 July 2026). DeepSeek models think before they reply unless thinking is switched off; while thinking, the temperature has no effect and the thinking counts towards the maximum response length.

## Language and libraries

Python. It uses the openai package (Apache License 2.0), OpenAI's Python SDK, which DeepSeek's OpenAI-compatible API also works with, and pandas (BSD 3-Clause). Omniscope installs openai with pip on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

- **Input 1**: the records to send, with a field holding each record's prompt.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| DeepSeek API key | `deepseekApiKey` | Password | A key from https://platform.deepseek.com/api_keys. Usage is billed to its DeepSeek account. |
| Model | `Model` | Text | The model ID, as listed at https://api-docs.deepseek.com/quick_start/pricing, for example deepseek-flash or deepseek-v4-pro. Default: `deepseek-flash`. |
| User prompt field | `Prompt` | Field | The field holding each record's prompt: the instruction and the text to work on. Build it with a Formula block if it combines several fields. Numbers and dates are sent as text; records with an empty prompt are not sent. |
| System prompt field | `SystemPrompt` | Field | Optional. A field holding instructions that set the model's role, rules and answer format, for example "Reply with one category only: Billing, Delivery or Other". Usually the same text on every record. |
| Temperature | `Temperature` | Number | Optional, 0 to 2. Lower values make replies more consistent, higher values more varied. Leave empty to use the model's default. DeepSeek ignores it while the model is thinking, which is on by default. |
| Maximum response length (tokens) | `MaxTokens` | Whole number | Optional. The most tokens each reply may use; in thinking mode this includes the reasoning. A token is roughly three-quarters of a word. Replies that reach the limit are cut short and marked in the Truncated field. Empty: DeepSeek's default. |
| Requests at a time | `Concurrency` | Whole number | How many requests are sent at the same time, 1 to 16. Higher finishes large inputs sooner; lower it if the service reports a rate limit. Default: `4`. |

## Outputs

- **Replies** (`Output Data`): the input records with **Response** (text) and **Truncated** (true or false; empty for records that were not sent) added.

## Limits

- Prompts and the records' text are sent to DeepSeek, and each request is billed to the key's account.
- Text only: no images or files.
- Each record is a separate, single-turn request: there is no conversation history between records, and no shared context beyond what the prompt and system prompt carry.
- Replies can differ between runs, even with the same prompt and settings.
- Every run sends every record with a prompt again. Filter the input to new records first if earlier replies are kept elsewhere.
- The tests send up to 400 records through a stand-in for the service; real throughput depends on DeepSeek's capacity and the model's speed (thinking makes each reply slower).

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented. `sample-data/placeholder.csv` is what the block outputs for it, using the invented replies in `tests/canned/`, for trying a workflow without a DeepSeek API key.
