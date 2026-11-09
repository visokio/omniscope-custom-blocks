# AI Chat - Google Gemini

Sends the prompt in each record to a Google Gemini model and adds the reply to the record.

Rewriting, tidying or summarising text one record at a time is a common job for a language model. This block does it inside a workflow with your own Gemini API key: nothing needs setting up in the server's AI settings, and requests are billed to, or count against the free quota of, the key's Google project.

- Choose the **User prompt field**: the text each record sends. An optional **System prompt field** carries the instructions (the model's role, the categories to choose from, the answer format); it is usually the same text on every record, made with a Formula block.
- The output is the input with two fields added: **Response**, the model's reply, and **Truncated**, true when the reply stopped at the maximum response length. If the input already has a Response field, the new ones are called Response 2 and Truncated 2.
- Records with an empty prompt are passed through with both fields empty and are not sent. Numbers and dates in the prompt field are sent as text.
- Requests can go several at a time (**Requests at a time**, 4 by default); the output keeps the input's order.
- If a request fails, the block stops with the service's message, the record number and a hint (for example "Check the API key"); there is no partial output.

The default model is `gemini-3.5-flash-lite`, Google's model for high-volume, cost-sensitive tasks (checked against Google's model list on 6 November 2026: the previous default, gemini-2.5-flash, is deprecated, and from 1 December 2026 its requests are routed to gemini-3.5-flash-lite). Gemini models think before they reply, and the thinking counts towards the maximum response length. Google recommends leaving the temperature at its default (1.0) for Gemini 3 models; the block sends one only when you set it.

## Language and libraries

Python. It uses the google-genai package (Apache License 2.0), Google's Gen AI SDK for Python, and pandas (BSD 3-Clause). Omniscope installs google-genai with pip on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

- **Input 1**: the records to send, with a field holding each record's prompt.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Gemini API key | `GEMINI_API_KEY` | Password | A key from Google AI Studio, https://aistudio.google.com/apikey. |
| Model | `Model` | Text | The model ID, as listed at https://ai.google.dev/gemini-api/docs/models, for example gemini-3.5-flash-lite or gemini-3.8-flash. Default: `gemini-3.5-flash-lite`. |
| User prompt field | `Prompt` | Field | The field holding each record's prompt: the instruction and the text to work on. Build it with a Formula block if it combines several fields. Numbers and dates are sent as text; records with an empty prompt are not sent. |
| System prompt field | `SystemPrompt` | Field | Optional. A field holding instructions that set the model's role, rules and answer format, for example "Reply with one category only: Billing, Delivery or Other". Usually the same text on every record. |
| Temperature | `Temperature` | Number | Optional, 0 to 2. Lower values make replies more consistent, higher values more varied. Leave empty to use the model's default. Google recommends the default (1.0) for Gemini 3 models. |
| Maximum response length (tokens) | `MaxTokens` | Whole number | Optional. The most tokens each reply may use; for thinking models this includes the thinking. A token is roughly three-quarters of a word. Replies that reach the limit are cut short and marked in the Truncated field. Empty: the model's default. |
| Requests at a time | `Concurrency` | Whole number | How many requests are sent at the same time, 1 to 16. Higher finishes large inputs sooner; lower it if the service reports a rate limit. Default: `4`. |

## Outputs

- **Replies** (`Output Data`): the input records with **Response** (text) and **Truncated** (true or false; empty for records that were not sent) added.

## Limits

- Prompts and the records' text are sent to Google. Check the Gemini API terms for how Google may use what is sent with a free-tier key before sending anything confidential.
- Text only: no images or files.
- Each record is a separate, single-turn request: there is no conversation history between records, and no shared context beyond what the prompt and system prompt carry.
- Replies can differ between runs, even with the same prompt and settings.
- Every run sends every record with a prompt again. Filter the input to new records first if earlier replies are kept elsewhere.
- The tests send up to 400 records through a stand-in for the service; real throughput depends on the key's rate limits (low on the free tier) and the model's speed.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented. `sample-data/placeholder.csv` is what the block outputs for it, using the invented replies in `tests/canned/`, for trying a workflow without a Gemini API key.
