# Send to Telegram

Sends the input records as a message to a Telegram chat, group or channel through your bot, as text, a table or JSON.

A short list computed in a workflow (items to reorder, failed checks, today's figures) is most useful on the phone of the person who acts on it. This block sends the input records to a Telegram chat as a message from your bot, at the end of a scheduled workflow or whenever it runs.

- **Text**: one line per record, the values separated by spaces. Missing values are left out; dates read `2025-03-03`.
- **Table**: a fixed-width table with the field names, sent as preformatted text so the columns line up on a phone.
- **JSON**: a list of records, numbers as numbers, dates as text, missing values as `null`.
- Telegram allows **4,096 characters** per message. A longer text is sent as several messages, split between records; a table repeats its header on each, and each JSON message is a complete list. A single record longer than a message is cut, with `…`.
- With **no input records, nothing is sent** (useful for alerts: no records, no message).
- If Telegram refuses a message (unknown chat, wrong token, bot not in the group), the block stops with Telegram's reason. Errors never show the bot token.

## Language and libraries

Python. It uses requests (Apache License 2.0) for Telegram's Bot API and pandas (BSD 3-Clause). pandas is part of Omniscope's Python environment; Omniscope installs requests with pip on first run if it is missing (the manifest's `dependencies`).

## Setting up Telegram

1. In Telegram, message **@BotFather**, send `/newbot` and follow the steps. It gives you the **bot token**, such as `7000000001:AA...`.
2. The **chat ID**:
   - a private chat: send your bot a message, then open `https://api.telegram.org/bot<token>/getUpdates` in a browser and read `chat.id`;
   - a group: add the bot to the group, send a message in it, and read `chat.id` the same way (group IDs start with `-`);
   - a public channel: add the bot as an administrator and use `@channelname`.

## Inputs

- **Input 1**: the records to send.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Bot token | `bot_token` | Password | From @BotFather. |
| Chat ID | `chat_id` | Text | A number (a group's starts with `-`), or `@channelname`. |
| Format | `text_format` | Choice | JSON (`JSON`), Table (`TABLE`), or Text, one line per record (`CONCAT`, the default). |

## Outputs

- **Sent** (`Output Data`): one record per message sent: `Part`, `Parts` (how many messages in all), `Records` (in that message), `Characters` (as Telegram counts them), `Message ID` (Telegram's), `Chat` (the chat's numeric ID).

## Limits

- The records are sent to Telegram's servers and can be read by everyone in the chat, group or channel (and anyone who can read a public channel): send only what they may see.
- Messages are sent one by one. Telegram limits bots to about 20 messages a minute in one group, so a very long table is better summarised before it is sent.
- Text and JSON are sent as plain text; Table is sent with Telegram's HTML formatting (`<pre>`), with `<`, `>` and `&` escaped.
- The tests use a stand-in for the Bot API that answers like Telegram (canned replies in `tests/canned/`, including its refusals); nothing is sent to Telegram.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented.
