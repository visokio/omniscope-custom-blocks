# AI Chat - Local LLM

Sends the prompt in each record to a language model running on your own machine or network, through an OpenAI-compatible endpoint, and adds the reply to the record.

Classifying or summarising free text is a common job for a language model, but some text should not leave the organisation. This block sends it only to the endpoint you enter: a model server on your own machine or network, such as llama.cpp, llamafile, Ollama, LM Studio or vLLM, all of which offer the OpenAI-compatible chat completions API it uses.

- Choose the **User prompt field**: the text each record sends. An optional **System prompt field** carries the instructions (the model's role, the categories to choose from, the answer format); it is usually the same text on every record, made with a Formula block.
- The output is the input with two fields added: **Response**, the model's reply, and **Truncated**, true when the reply stopped at the maximum response length. If the input already has a Response field, the new ones are called Response 2 and Truncated 2.
- Records with an empty prompt are passed through with both fields empty and are not sent. Numbers and dates in the prompt field are sent as text.
- Requests can go several at a time (**Requests at a time**, 1 by default); the output keeps the input's order.
- If a request fails, the block stops with the service's message, the record number and a hint (for example "Check the API key"); there is no partial output.

The **Endpoint** is the server's base address, usually ending in `/v1`: for example `http://localhost:8080/v1` for llama.cpp or llamafile, `http://localhost:11434/v1` for Ollama. The address is resolved on the Omniscope server, not in your browser; if Omniscope runs Python in Docker, `localhost` is the container, so use the machine's name or address. The **Model** is the name the server expects (servers that hold one model accept any name; the default, `LLaMA_CPP`, is llamafile's). An API key is needed only if the server asks for one. Requests at a time is 1 by default, because many local servers answer one request at a time.

## Language and libraries

Python. It uses the openai package (Apache License 2.0), OpenAI's Python SDK, used here only as a client for OpenAI-compatible servers, and pandas (BSD 3-Clause). Omniscope installs openai with pip on first run if it is missing (the manifest's `dependencies`); pandas is part of Omniscope's Python environment.

## Inputs

- **Input 1**: the records to send, with a field holding each record's prompt.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Endpoint | `ModelEndpoint` | Text | The base address of an OpenAI-compatible API, usually ending in /v1, for example http://localhost:8080/v1 (llama.cpp, llamafile) or http://localhost:11434/v1 (Ollama). Resolved on the Omniscope server. |
| API key | `ApiKey` | Password | Optional. Only if your server asks for one; most local servers don't. |
| Model | `Model` | Text | The model name your server expects, for example the name listed by its /v1/models page. Servers that hold one model (llama.cpp, llamafile) accept any name. Default: `LLaMA_CPP`. |
| User prompt field | `Prompt` | Field | The field holding each record's prompt: the instruction and the text to work on. Build it with a Formula block if it combines several fields. Numbers and dates are sent as text; records with an empty prompt are not sent. |
| System prompt field | `SystemPrompt` | Field | Optional. A field holding instructions that set the model's role, rules and answer format, for example "Reply with one category only: Billing, Delivery or Other". Usually the same text on every record. |
| Temperature | `Temperature` | Number | Optional, 0 to 2. Lower values make replies more consistent, higher values more varied. Leave empty to use the model's default. Some servers cap it at 1 or ignore it. |
| Maximum response length (tokens) | `MaxTokens` | Whole number | Optional. The most tokens each reply may use. A token is roughly three-quarters of a word. Replies that reach the limit are cut short and marked in the Truncated field. Empty: the server's default. |
| Requests at a time | `Concurrency` | Whole number | How many requests are sent at the same time, 1 to 16. Higher finishes large inputs sooner; lower it if the service reports a rate limit. Most local servers answer one request at a time unless set up for more. Default: `1`. |

## Outputs

- **Replies** (`Output Data`): the input records with **Response** (text) and **Truncated** (true or false; empty for records that were not sent) added.

## Limits

- The data goes only to the endpoint you enter. Whether the server keeps or logs prompts is up to the server's own settings. With an `http://` endpoint on another machine, prompts and replies cross the network unencrypted; use `https://` where the server offers it.
- Text only: no images or files. Parameters beyond temperature and maximum length are not sent.
- Each record is a separate, single-turn request: there is no conversation history between records, and no shared context beyond what the prompt and system prompt carry.
- Replies can differ between runs, even with the same prompt and settings.
- Every run sends every record with a prompt again. Filter the input to new records first if earlier replies are kept elsewhere.
- The tests send up to 400 records through a stand-in for the service; real throughput depends on the server's hardware and the model's size; large models can take a minute or more per reply.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented. `sample-data/placeholder.csv` is what the block outputs for it, using the invented replies in `tests/canned/`, for trying a workflow without a model server.
