# AI Chat - OpenAI GPT

Sends the prompt in each record to an OpenAI model and adds the reply to the record.

Reading free text and turning it into something countable (a topic, a label, a short summary) is a common job for a language model. This block does it inside a workflow with your own OpenAI API key: nothing needs setting up in the server's AI settings, and every request is billed to that key's account.

- Choose the **User prompt field**: the text each record sends. An optional **System prompt field** carries the instructions (the model's role, the categories to choose from, the answer format); it is usually the same text on every record, made with a Formula block.
- The output is the input with two fields added: **Response**, the model's reply, and **Truncated**, true when the reply stopped at the maximum response length. If the input already has a Response field, the new ones are called Response 2 and Truncated 2.
- Records with an empty prompt are passed through with both fields empty and are not sent. Numbers and dates in the prompt field are sent as text.
- Requests can go several at a time (**Requests at a time**, 4 by default); the output keeps the input's order.
- If a request fails, the block stops with the service's message, the record number and a hint (for example "Check the API key"); there is no partial output.

The default model is `gpt-6-luna`, OpenAI's model for high-volume tasks (checked against OpenAI's model list on 6 November 2026; the previous default, gpt-3.5-turbo, was shut down on 23 October 2026). The block uses the Chat Completions API, so the model must support it. Current GPT models reason before they reply: they accept a temperature only with reasoning switched off, and the reasoning counts towards the maximum response length, so leave both empty unless you need them.

## Language and libraries

Python. It uses the openai package (Apache License 2.0), OpenAI's Python SDK, and pandas (BSD 3-Clause). Omniscope installs openai with pip on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

- **Input 1**: the records to send, with a field holding each record's prompt.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| OpenAI API key | `OpenAiApiKey` | Password | A secret key from https://platform.openai.com/api-keys. Usage is billed to its OpenAI account. |
| Model | `Model` | Text | The model ID, as listed at https://developers.openai.com/api/docs/models, for example gpt-6-luna or gpt-6.1-sol. It must support the Chat Completions API. Default: `gpt-6-luna`. |
| User prompt field | `Prompt` | Field | The field holding each record's prompt: the instruction and the text to work on. Build it with a Formula block if it combines several fields. Numbers and dates are sent as text; records with an empty prompt are not sent. |
| System prompt field | `SystemPrompt` | Field | Optional. A field holding instructions that set the model's role, rules and answer format, for example "Reply with one category only: Billing, Delivery or Other". Usually the same text on every record. |
| Temperature | `Temperature` | Number | Optional, 0 to 2. Lower values make replies more consistent, higher values more varied. Leave empty to use the model's default. Current GPT models accept a temperature only when reasoning is switched off, so leave it empty for them. |
| Maximum response length (tokens) | `MaxTokens` | Whole number | Optional. The most tokens each reply may use, including the model's hidden reasoning, so a low limit can leave the reply empty. A token is roughly three-quarters of a word. Replies that reach the limit are cut short and marked in the Truncated field. Empty: the model's own maximum. |
| Requests at a time | `Concurrency` | Whole number | How many requests are sent at the same time, 1 to 16. Higher finishes large inputs sooner; lower it if the service reports a rate limit. Default: `4`. |

## Outputs

- **Replies** (`Output Data`): the input records with **Response** (text) and **Truncated** (true or false; empty for records that were not sent) added.

## Limits

- Prompts and the records' text are sent to OpenAI, and each request is billed to the key's account.
- Text only: no images or files. Chat Completions only, no built-in tools.
- Each record is a separate, single-turn request: there is no conversation history between records, and no shared context beyond what the prompt and system prompt carry.
- Replies can differ between runs, even with the same prompt and settings.
- Every run sends every record with a prompt again. Filter the input to new records first if earlier replies are kept elsewhere.
- The tests send up to 400 records through a stand-in for the service; real throughput depends on OpenAI's rate limits for your account and the model's speed.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented. `sample-data/placeholder.csv` is what the block outputs for it, using the invented replies in `tests/canned/`, for trying a workflow without an OpenAI API key.
